from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.views.decorators.http import require_POST

from user_feedback.experiments import get_experiment
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
        # get_client_ip returns "-" when there is no proxy header; store NULL then,
        # since "-" is not a valid value for the ip column.
        ip = get_client_ip(request)
        experiment.save_response(request.user, form.cleaned_data, ip=ip if ip != "-" else None)
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


def page_items(request):
    """Returns the HTML of an experiment that loads after the page loads (see Experiment.loads_after_page),
    as pieces that experiments.js places in the page.

    The request has the same GET parameters as the page, plus the experiment (``experiment_id``)
    and the sounds shown in the page (``experiment_sound_ids``).
    """
    experiment = get_experiment(request.GET.get("experiment_id", ""))
    # Experiments are only shown to logged-in users.
    if experiment is None or not experiment.loads_after_page or not request.user.is_authenticated:
        return JsonResponse({"items": []})
    sound_ids = [
        int(sound_id) for sound_id in request.GET.get("experiment_sound_ids", "").split(",") if sound_id.isdigit()
    ]
    return JsonResponse({"items": experiment.render_page_items(request, sound_ids)})
