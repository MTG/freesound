# Each experiment is a subclass of Experiment (see base.py) in its own module of this package.

from django.conf import settings
from django.utils.module_loading import import_string

# The registry is built from settings.FEEDBACK_EXPERIMENTS, the place experiments are.
EXPERIMENTS = {
    experiment_id: import_string(config["class"])() for experiment_id, config in settings.FEEDBACK_EXPERIMENTS.items()
}


def get_experiment(experiment_id):
    return EXPERIMENTS.get(experiment_id)
