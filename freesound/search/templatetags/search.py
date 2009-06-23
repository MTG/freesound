from django import template
from tags.templatetags.tagcloud import size_generator, annotate

register = template.Library()

@register.inclusion_tag('search/facet.html', takes_context=True)
def display_facet(context, filter, facet, type):
    if facet:
        unique_counts = sorted(dict((count, 1) for (item, count) in facet).keys())
        small_size = 0.5
        large_size = 1.5
        lookup = dict(zip(unique_counts, size_generator(small_size, large_size, len(unique_counts))))

        if type == "cloud":
            facet.sort(cmp=lambda x, y: cmp(x[0].lower(), y[0].lower()))
            
        facet = [dict(item=item,count=count,size=lookup[count]) for (item,count) in facet if item != "0"]

    context.update({"facet":facet, "type":type, "filter":filter})
    
    return context