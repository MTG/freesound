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

register = template.Library()


@register.inclusion_tag('geotags/display_geotags.html', takes_context=True)
def display_geotags(context, url='/geotags/geotags_box_barray/', width=900, height=600, clusters='on', center_lat=None, center_lon=None, zoom=None, username=None, tag=None):
    if center_lat and center_lon and zoom:
        borders = 'defined'
    else:
        borders = 'automatic'

    return {'url': url,
            'media_url': context['media_url'],
            'm_width': width,
            'm_height': height,
            'clusters': clusters,
            'center_lat': center_lat,
            'center_lon': center_lon,
            'zoom': zoom,
            'borders': borders,
            'username': username,
            'tag': tag}
