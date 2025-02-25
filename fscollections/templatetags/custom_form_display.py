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

@register.simple_tag
def custom_form_display (form, display_fields):
    """This function is used to display only certain fields in a Django form. 

    Args:
        form (forms.Form or forms.ModelForm): the form to be displayed
        display_fields (str array): array containing the field names to be rendered in the html  

    Returns:
        array: contains the form fields to be displayed
    """
    return [field for field in form if field.name in display_fields]

    
