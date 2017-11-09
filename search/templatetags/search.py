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


from django import template
from django.utils.http import urlquote_plus
from utils.tags import annotate_tags

register = template.Library()


@register.inclusion_tag('search/facet.html', takes_context=True)
def display_facet(context, flt, facet, type):
    facet = annotate_tags([dict(name=f[0], count=f[1]) for f in facet if f[0] != "0"],
                          sort=True, small_size=0.7, large_size=2.0)

    # If the filter is grouping_pack and there are elements which do not contain the character "_" means that
    # these sounds do not belong to any pack (as grouping pack values should by "packId_packName" if there is a pack
    # or "soundId" if there is no pack assigned. We did this to be able to filter properly in the facets, as pack names
    # are not unique!. What we do then is filter out the facet elements where, only for the case of grouping_pack,
    # the element name is a single number that does not contain the character "_"

    filter_query = context['filter_query']
    filtered_facet = []
    for element in facet:
        if flt == "grouping_pack":
            if element['name'].count("_") > 0:
                # We also modify the dispay name to remove the id
                element['display_name'] = element['name'][element['name'].find("_")+1:]
                element['params'] = '%s %s:"%s"' % (filter_query, flt, urlquote_plus(element['name']))
                filtered_facet.append(element)
        else:
            element['display_name'] = element['name']
            element['params'] = '%s %s:"%s"' % (filter_query, flt, urlquote_plus(element['name']))
            filtered_facet.append(element)
    context.update({"facet": filtered_facet, "type": type, "filter": flt})
    return context
