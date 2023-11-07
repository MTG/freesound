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

from sounds.models import License

register = template.Library()

@register.inclusion_tag('sounds/license_form.html', takes_context=True)
def display_license_form(context, form):
    # NOTE: this is only used in old UI and can be safely removed when fully migrating to BW
    cc0_license_id = License.objects.get(name__iexact='Creative Commons 0').id
    cc_by_license_id =  License.objects.get(name__iexact="Attribution", deed_url__contains="4.0").id
    cc_by_nc_license_id = License.objects.get(name__iexact="Attribution NonCommercial", deed_url__contains="4.0").id    
    return {
        'form': form, 
        'cc0_license_id': cc0_license_id, 
        'cc_by_license_id': cc_by_license_id, 
        'cc_by_nc_license_id': cc_by_nc_license_id
    }
