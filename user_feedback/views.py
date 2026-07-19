from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.views.decorators.http import require_POST

from user_feedback.experiments import get_experiment


@login_required
@require_POST
def submit(request):
    """Save one feedback answer for any experiment, then send the user back where
    they came from.

    Generic: the experiment is named in the POST (``experiment_id``). Each
    experiment supplies its own form (``form_class``), which validates its own
    fields; so this view stays the same.
    """
    experiment = get_experiment(request.POST.get("experiment_id", ""))
    if experiment is None:
        raise Http404("Unknown experiment")
    form = experiment.form_class(request.POST)
    if form.is_valid():
        experiment.save_response(request.user, form.cleaned_data)
    # Whether it saved or not, just return to the page the box was shown on.
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
