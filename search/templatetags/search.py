from django import template
from utils.tags import annotate_tags

register = template.Library()

@register.inclusion_tag('search/facet.html', takes_context=True)
def display_facet(context, filter, facet, type):
    facet = annotate_tags([dict(name=f[0], count=f[1]) for f in facet if f[0] != "0"], sort=True, small_size=0.7, large_size=2.0)

    # If the filter is grouping_pack and there are elements which do not contain the character "_" means that
    # these sounds do not belong to any pack (as grouping pack values should by "packId_packName" if there is a pack
    # or "soundId" if there is no pack assigned. We did this to be able to filter properly in the facets, as pack names
    # are not unique!. What we do then is filter out the facet elements where, only for the case of grouping_pack,
    # the element name is a single number that does not contain the character "_"

    filter_query = context['filter_query']
    filtered_facet = []
    for element in facet:
        if filter == "grouping_pack":
            if element['name'].count("_") > 0:
                element['display_name'] = element['name'][element['name'].find("_")+1:] # We also modify the dispay name to remove the id
                element['params'] = '%s %s:"%s"' % (filter_query, filter, element['name'])
                filtered_facet.append(element)
        else:
            element['display_name'] = element['name']
            element['params'] = '%s %s:"%s"' % (filter_query, filter, element['name'])
            filtered_facet.append(element)
    context.update({"facet":filtered_facet, "type":type, "filter":filter})
    return context