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
from django.conf import settings

from sounds.models import License
from utils.search import search_query_processor_options
from utils.search.backends.solr555pysolr import FIELD_NAMES_MAP
from utils.tags import annotate_tags

register = template.Library()


@register.inclusion_tag('search/facet.html', takes_context=True)
def display_facet(context, facet_name, facet_title=None):
    sqp = context['sqp']
    facets = context['facets']
    solr_fieldname = FIELD_NAMES_MAP.get(facet_name, facet_name)
    if facet_name in facets:
        facet_title = sqp.facets[facet_name].get('title', facet_name.capitalize())
        facet_type = sqp.facets[facet_name].get('widget', 'list')

        # If a facet contains a value which is already used in a filter (this can hapen with facets with multiple values like
        # tags), then we remove it from the list of options so we don't show redundant information
        facet_values_to_skip = []
        for field_name_value in sqp.get_active_filters():
            if field_name_value.startswith(solr_fieldname + ':'):
                facet_values_to_skip.append(field_name_value.split(':')[1].replace('"', ''))
        if facet_values_to_skip:
            facets[facet_name] = [f for f in facets[facet_name] if f[0] not in facet_values_to_skip]
        
        # Annotate facet elements with size values used in the tag cloud
        if facet_type == 'cloud':
            facet = annotate_tags([dict(value=f[0], count=f[1]) for f in facets[facet_name] if f[0] != "0"], small_size=0.7, large_size=2.0)
        else:
            facet = [{'value': value, 'count': count, 'size': -1} for value, count in facets[facet_name]]
    else:
        # Return "empty" data (facet will not be displayed)
        return {'type': 'list', 'title': facet_name, 'facet': []}

    # If the filter is grouping_pack and there are elements which do not contain the character "_" means that
    # these sounds do not belong to any pack (as grouping pack values should by "packId_packName" if there is a pack
    # or "soundId" if there is no pack assigned. We did this to be able to filter properly in the facets, as pack names
    # are not unique!. What we do then is filter out the facet elements where, only for the case of grouping_pack,
    # the element name is a single number that does not contain the character "_"

    # We add the extra Free Cultural Works license facet
    if facet_name == 'license':
        fcw_count = 0
        only_fcw_in_facet = True
        for element in facet:
            if element['value'].lower() == 'attribution' or element['value'].lower() == 'creative commons 0':
                fcw_count += element['count']
            else:
                only_fcw_in_facet = False
        if fcw_count and not only_fcw_in_facet:
            facet = [{
                    'value': settings.FCW_FILTER_VALUE,
                    'count': fcw_count,
                    'size': 1.0,
                }] + facet

    # Remove "no pack" elements form pack facet (no pack elements are those in which "grouping pack" only has the sound id and not any pack id/name)
    if facet_name == "grouping_pack":
        facet = [element for element in facet if '_' in element['value']]

    for element in facet:
        # Set display values (the values how they'll be shown in the UI)
        if facet_name == "grouping_pack":
            # Modify the display name to remove the pack id
            element['display_value'] = element['value'][element['value'].find("_")+1:]
        elif element['value'] == settings.FCW_FILTER_VALUE:
            element['display_value'] = "Approved for Free Cultural Works"
        elif facet_name == 'license':
            # License field in solr is case insensitive and will return facet names in lowercase. 
            # We need to properly capitalize them to use official CC license names.
            element['display_value'] = element['value'].title().replace('Noncommercial', 'NonCommercial')
        elif facet_type == 'range':
            # Update display value for range facets
            gap = sqp.facets[facet_name]['gap']
            element['display_value'] = f'{float(element["value"]):.1f} - {float(element["value"]) + gap:.1f}'
        else:
            # In all other cases, use the value as is for display purposes
            element['display_value'] = element['value']
        
        # Set the URL to add facet values as filters
        if facet_type != 'range':
            if element["value"].startswith('('):
                # If the filter value is a "complex" operation , don't wrap it in quotes
                filter_str = f'{solr_fieldname}:{element["value"]}'
            elif element["value"].isdigit():
                # If the filter value is a digit, also don't wrap it in quotes
                filter_str = f'{solr_fieldname}:{element["value"]}'
            else:
                # Otherwise wrap in quotes
                filter_str = f'{solr_fieldname}:"{element["value"]}"'
        else:
            # For facets of type range, the filter must be constructed as a range
            gap = sqp.facets[facet_name]['gap']
            filter_str = f'{solr_fieldname}:[{element["value"]} TO {float(element["value"]) + gap}]'
        element['add_filter_url'] = sqp.get_url(add_filters=[filter_str])
        
    # We compute weight for the opacity filter on "could" type facets
    if facet_type == 'cloud':
        max_count = max([element['count'] for element in facet])
        for element in facet:
            element['weight'] = element['count'] / max_count

    # For facets with "resort" option, carry out the sorting based on the value
    if sqp.facets[facet_name].get('resort_by_value_as_int', False):
        facet = sorted(facet, key=lambda x: int(x['value']))

    # Skip value of "0" if indicated
    if sqp.facets[facet_name].get('skip_value_0', False):
        facet = [f for f in facet if int(f['value']) != 0]

    # We also add icons to license facets
    if facet_name == 'license':
        for element in facet:
            if element['value'] != settings.FCW_FILTER_VALUE:
                element['icon'] = License.bw_cc_icon_name_from_license_name(element['display_value'])
            else:
                element['icon'] = 'fcw'

    return {'type': facet_type, 'title': facet_title, 'facet': facet}


@register.inclusion_tag('search/search_option.html', takes_context=True)
def display_search_option(context, option_name, widget=None):
    sqp = context['sqp']
    option = sqp.options[option_name]
    if widget is None:
        # If a widget is not provided as a parameter, use a sensible default
        widget = {
            search_query_processor_options.SearchOptionBool: 'checkbox',
            search_query_processor_options.SearchOptionBoolFilterInverted: 'checkbox',
            search_query_processor_options.SearchOptionStr: 'text',
            search_query_processor_options.SearchOptionChoice: 'select',
        }.get(type(option), 'text')
    label = option.label if option.label else option_name.capitalize().replace('_', ' ')
    return {'option': option, 'option_name': option_name, 'label': label, 'widget': widget}