# Each experiment is a subclass of Experiment (see base.py) in its own module of this package.

from django.conf import settings
from django.utils.module_loading import import_string

# The registry is built from settings.FEEDBACK_EXPERIMENTS, the place experiments are.
EXPERIMENTS = {
    experiment_id: import_string(config["class"])() for experiment_id, config in settings.FEEDBACK_EXPERIMENTS.items()
}


def get_experiment(experiment_id):
    return EXPERIMENTS.get(experiment_id)


def page_loads_experiments(request):
    """True if some experiment is loaded in the page of the request after it loads (see page_url_name)."""
    url_name = request.resolver_match.url_name if request.resolver_match else None
    return any(
        experiment.page_url_name == url_name and (request.user.is_authenticated or not experiment.requires_login)
        for experiment in EXPERIMENTS.values()
        if experiment.page_url_name
    )
