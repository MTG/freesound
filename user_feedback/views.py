from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.urls import Resolver404, resolve
from django.views.decorators.http import require_POST

from user_feedback.experiments import EXPERIMENTS, get_experiment
from utils.logging_filters import get_client_ip


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
    if experiment.requires_login and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    is_ajax = bool(request.GET.get("ajax"))
    form = experiment.form_class(request.POST)
    if form.is_valid():
        # get_client_ip returns "-" when there is no proxy header; store NULL then,
        # since "-" is not a valid value for the ip column.
        ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        experiment.save_response(user, form.cleaned_data, ip=ip if ip != "-" else None)
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
    """Returns the HTML of the experiments of a page, as pieces that experiments.js places in the page.
    It is requested after the page loads, so the template of the page does not need to change.

    The request has the same GET parameters as the page, plus the path of the page
    (``experiment_path``) and the sounds shown in it (``experiment_sound_ids``).
    """
    try:
        url_name = resolve(request.GET.get("experiment_path", "")).url_name
    except Resolver404:
        return JsonResponse({"items": []})
    sound_ids = [
        int(sound_id) for sound_id in request.GET.get("experiment_sound_ids", "").split(",") if sound_id.isdigit()
    ]
    items = []
    for experiment in EXPERIMENTS.values():
        if experiment.requires_login and not request.user.is_authenticated:
            continue
        if experiment.page_url_name == url_name:
            items += experiment.render_page_items(request, sound_ids)
    return JsonResponse({"items": items})
