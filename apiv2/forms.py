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

import django.forms as forms

class ApiV2ClientForm(forms.Form):
    name          = forms.CharField(label='Application name')
    url           = forms.URLField(label='Application url')
    redirect_uri  = forms.URLField(label='Your application\'s callback URL')
    description   = forms.CharField(label='Describe your application', widget=forms.Textarea)
    accepted_tos  = forms.BooleanField(label='',
                                       help_text='Check this box to accept the <a href="/help/tos_api/" target="_blank">terms of use</a> of the Freesound API',
                                       required=True,
                                       error_messages={'required': 'You must accept the terms of use in order to get access to the API.'})
