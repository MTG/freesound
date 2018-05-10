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
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag()
def maps_js_scripts():
    html = '<script type="text/javascript" src="//maps.googleapis.com/maps/api/js?v=3&key=%s"></script>' \
           % settings.GOOGLE_API_KEY
    html += '<script src="%s/js/markerclustererV3.js" type="text/javascript"></script>' % settings.MEDIA_URL
    html += '<script src="%s/js/maps.js?v={{ last_restart_date }}" type="text/javascript"></script>' % settings.MEDIA_URL
    return mark_safe(html)
