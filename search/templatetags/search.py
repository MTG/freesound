from django import template
from utils.tags import annotate_tags

register = template.Library()

@register.inclusion_tag('search/facet.html', takes_context=True)
def display_facet(context, filter, facet, type):
    facet = annotate_tags([dict(name=f[0], count=f[1]) for f in facet if f[0] != "0"], sort=True, small_size=0.5, large_size=1.5)
    context.update({"facet":facet, "type":type, "filter":filter})
    return context