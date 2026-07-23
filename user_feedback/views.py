from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
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

    Two response modes: a normal POST gets a redirect back, while a POST with
    ``?ajax=1`` gets JSON on success or the re-rendered form HTML on validation
    error so a JS caller can swap the errors in place.
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
        return render(request, experiment.modal_template, {"form": form, **experiment.modal_context(request, form)})
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
def modal(request):
    """Render an experiment's follow-up modal, fetched by the modal JS."""
    experiment = get_experiment(request.GET.get("experiment_id", ""))
    if experiment is None or experiment.modal_template is None:
        raise Http404("Unknown experiment")
    # Query string doubles as the form's initial data, so the modal knows its context
    # (which sound, which answer) without this view knowing any experiment's fields.
    form = experiment.form_class(initial=request.GET.dict())
    return render(request, experiment.modal_template, {"form": form, **experiment.modal_context(request, form)})
