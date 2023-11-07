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

register = template.Library()


@register.inclusion_tag('templatetags/maps_js_scripts.html', takes_context=True)
def maps_js_scripts(context):
    # TODO: this will no longer be needed with BW as the equivalent is implemented in bw_templatetags
    return {'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN}
