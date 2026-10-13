from django import template
from django.utils.safestring import mark_safe

from user_feedback.experiments import EXPERIMENTS

register = template.Library()


@register.simple_tag(takes_context=True)
def feedback_experiments(context, page, **kwargs):
    """Returns the inline boxes of the experiments of a page (see Experiment.inline_page).
    The other arguments are passed to the experiments, e.g. the sound of the sound page."""
    request = context["request"]
    boxes = [
        experiment.render_inline_html(request, **kwargs)
        for experiment in EXPERIMENTS.values()
        if experiment.inline_page == page
    ]
    return mark_safe("".join(boxes))
