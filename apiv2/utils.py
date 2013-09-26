# -*- coding: utf-8 -*-

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

from provider.oauth2.views import AccessTokenView
from provider.views import OAuthError
from provider.oauth2.forms import PasswordGrantForm


class AccessTokenView(AccessTokenView):

    '''
    We override only a function of the AccessTokenView class in order to be able to set different
    allowed grant types per API client.
    '''

    def get_password_grant(self, request, data, client):
        if not client.apiv2_client.allow_oauth_passoword_grant:
            raise OAuthError({'error': 'unsupported_grant_type'})

        form = PasswordGrantForm(data, client=client)
        if not form.is_valid():
            raise OAuthError(form.errors)
        return form.cleaned_data