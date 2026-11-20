from django import template

from user_feedback.experiments import get_experiment

register = template.Library()


@register.simple_tag(takes_context=True)
def feedback_experiment(context, experiment_id, **kwargs):
    """Returns the HTML of an experiment (see Experiment.render_inline_html), or "" when it should not show now.
    The other arguments are passed to the experiment, e.g. the sound of the sound page.
    An experiment that is not in settings.FEEDBACK_EXPERIMENTS is not shown, so it can be
    removed without changing the templates that place it."""
    experiment = get_experiment(experiment_id)
    if experiment is None:
        return ""
    return experiment.render_inline_html(context["request"], **kwargs)
