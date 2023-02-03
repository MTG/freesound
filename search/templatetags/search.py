#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#


from past.utils import old_div
from django import template
from django.utils.http import urlquote_plus

from utils.frontend_handling import using_beastwhoosh
from utils.tags import annotate_tags

register = template.Library()


@register.inclusion_tag('search/facet.html', takes_context=True)
def display_facet(context, flt, facet, facet_type, title=""):
    facet = annotate_tags([dict(name=f[0], count=f[1]) for f in facet if f[0] != "0"],
                          sort="name", small_size=0.7, large_size=2.0)

    # If the filter is grouping_pack and there are elements which do not contain the character "_" means that
    # these sounds do not belong to any pack (as grouping pack values should by "packId_packName" if there is a pack
    # or "soundId" if there is no pack assigned. We did this to be able to filter properly in the facets, as pack names
    # are not unique!. What we do then is filter out the facet elements where, only for the case of grouping_pack,
    # the element name is a single number that does not contain the character "_"

    filter_query = urlquote_plus(context['filter_query'])
    filtered_facet = []
    for element in facet:
        if flt == "grouping_pack":
            if element['name'].count("_") > 0:
                # We also modify the display name to remove the id
                element['display_name'] = element['name'][element['name'].find("_")+1:]
                element['params'] = f"{filter_query} {flt}:\"{urlquote_plus(element['name'])}\""
            else:
                # If facet element belongs to "grouping pack" filter but does not have the "_" character in it, it
                # means this corresponds to the "no pack" grouping which we don't want to show as a facet element.
                continue
        else:
            element['display_name'] = element['name']

        element['params'] = f"{filter_query} {flt}:\"{urlquote_plus(element['name'])}\""
        element['id'] = f"{flt}--{urlquote_plus(element['name'])}"
        element['add_filter_url'] = '.?g={}&only_p={}&q={}&f={}&s={}&w={}'.format(
            context['group_by_pack_in_request'],
            context['only_sounds_with_pack'],
            context['search_query'],
            element['params'],
            context['sort'] if context['sort'] is not None else '',
            context['weights'] or ''
        )
        filtered_facet.append(element)

    if using_beastwhoosh(context['request']):
        # In BW ui, we sort the facets of type "cloud" by their frequency of occurrence and apply an opacity filter
        if filtered_facet:
            filtered_facet = sorted(filtered_facet, key=lambda x: x['count'], reverse=True)
            max_count = max([element['count'] for element in filtered_facet])
            for element in filtered_facet:
                element['weight'] = old_div((1.0 * element['count']), max_count)

    context.update({
        "facet": filtered_facet,
        "type": facet_type,
        "filter": flt,
        "title": title
    })
    return context
