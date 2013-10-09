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

from provider.views import OAuthError
from provider.scope import to_names, to_int
from provider.oauth2.views import AccessTokenView as DjangoRestFrameworkAccessTokenView
from provider.oauth2.forms import PasswordGrantForm
from provider.oauth2.models import RefreshToken, AccessToken


class AccessTokenView(DjangoRestFrameworkAccessTokenView):

    '''
    We override only a function of the AccessTokenView class in order to be able to set different
    allowed grant types per API client and to resctrict scopes on a client basis.
    '''

    def get_password_grant(self, request, data, client):
        if not client.apiv2_client.allow_oauth_passoword_grant:
            raise OAuthError({'error': 'unsupported_grant_type'})

        form = PasswordGrantForm(data, client=client)
        if not form.is_valid():
            raise OAuthError(form.errors)
        return form.cleaned_data

    def create_access_token(self, request, user, scope, client):

        # Filter out requested scopes and only leave those allowed to the client
        client_scope = client.apiv2_client.get_scope_display()
        allowed_scopes = [requested_scope for requested_scope in to_names(scope) if requested_scope in client_scope]

        return AccessToken.objects.create(
            user=user,
            client=client,
            scope=to_int(*allowed_scopes)
        )

    def create_refresh_token(self, request, user, scope, access_token, client):

        return RefreshToken.objects.create(
            user=user,
            access_token=access_token,
            client=client
        )


def get_authentication_details_form_request(request):
    auth_method_name = None
    user = None
    developer = None

    if request.successful_authenticator:
        auth_method_name = request.successful_authenticator.authentication_method_name
        if auth_method_name == "OAuth2":
            user = request.user
            developer = request.auth.client.user
        elif auth_method_name == "Token":
            user = None
            developer = request.auth.user
        elif auth_method_name == "Session":
            user = request.user
            developer = None

    return auth_method_name, developer, user