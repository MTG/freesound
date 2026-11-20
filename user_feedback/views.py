from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_POST

from user_feedback.experiments import get_experiment
from user_feedback.experiments.base import PageEventsForm
from utils.geoip import get_country_iso_code
from utils.logging_filters import get_client_ip


@login_required
@require_POST
def submit(request):
    """Save one feedback answer for any experiment, then send the user back where
    they came from.

    Generic: the experiment is named in the POST (``experiment_id``). Each
    experiment supplies its own form (``form_class``), which validates its own
    fields; so this view stays the same.

    Two response modes: a normal POST redirects back and an ``?ajax=1`` POST instead gets
    JSON with the saved answer, or the validation errors with a 400.
    """
    experiment = get_experiment(request.POST.get("experiment_id", ""))
    if experiment is None:
        raise Http404("Unknown experiment")
    is_ajax = bool(request.GET.get("ajax"))
    form = experiment.form_class(request.POST)
    if form.is_valid():
        # Only the country of the IP is stored, never the IP itself.
        country_iso_code = get_country_iso_code(get_client_ip(request))
        experiment.save_response(request.user, form.cleaned_data, country_iso_code=country_iso_code)
        if is_ajax:
            return JsonResponse({"success": True})
    elif is_ajax:
        # Errors as JSON with a 400 so the JS takes its error path (200 would read as success).
        return JsonResponse({"success": False, "errors": form.errors.get_json_data()}, status=400)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@require_POST
def opt_out(request):
    """Record a permanent 'don't ask again' for any experiment (keyed by experiment_id)."""
    experiment = get_experiment(request.POST.get("experiment_id", ""))
    if experiment is None:
        raise Http404("Unknown experiment")
    experiment.opt_out(request.user)
    if request.GET.get("ajax"):
        return JsonResponse({"success": True})
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@require_POST
def page_events(request):
    """Save when the page of a sound list experiment was hidden and seen again (see PageEventsForm)."""
    experiment = get_experiment(request.POST.get("experiment_id", ""))
    if experiment is None or not hasattr(experiment, "save_page_events"):
        raise Http404("Unknown experiment")
    form = PageEventsForm(request.POST)
    if not form.is_valid():
        return HttpResponse(status=400)
    country_iso_code = get_country_iso_code(get_client_ip(request))
    experiment.save_page_events(request.user, form.cleaned_data, country_iso_code=country_iso_code)
    return HttpResponse(status=204)
