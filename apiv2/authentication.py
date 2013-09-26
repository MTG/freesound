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

from django.core.exceptions import ImproperlyConfigured
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header
from rest_framework.authentication import BaseAuthentication
from apiv2.models import ApiV2Client
import provider.oauth2 as oauth2_provider
import datetime
provider_now = datetime.datetime.now

'''
We overwrite OAuth2Authentication from rest_framework.authentication because of a problem when importing provider_now.
Django-oauth2-provider tries to import a function only present in django >= 1.4 (django.utils.timezone), and we
are using 1.3.

We may use this overwritten class to add some extra funcitonality.
'''


class OAuth2Authentication(BaseAuthentication):
    """
    OAuth 2 authentication backend using `django-oauth2-provider`
    """
    www_authenticate_realm = 'api'

    def __init__(self, *args, **kwargs):
        super(OAuth2Authentication, self).__init__(*args, **kwargs)

        if oauth2_provider is None:
            raise ImproperlyConfigured(
                "The 'django-oauth2-provider' package could not be imported. "
                "It is required for use with the 'OAuth2Authentication' class.")

    def authenticate(self, request):
        """
        Returns two-tuple of (user, token) if authentication succeeds,
        or None otherwise.
        """

        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'bearer':
            return None

        if len(auth) == 1:
            msg = 'Invalid bearer header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid bearer header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(request, auth[1])

    def authenticate_credentials(self, request, access_token):
        """
        Authenticate the request, given the access token.
        """

        try:
            token = oauth2_provider.models.AccessToken.objects.select_related('user','client')
            # provider_now switches to timezone aware datetime when
            # the oauth2_provider version supports to it.
            token = token.get(token=access_token, expires__gt=provider_now())
        except oauth2_provider.models.AccessToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        user = token.user

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        if not token.client.apiv2_client.status == 'OK':
            raise exceptions.AuthenticationFailed('Suspended token or token pending for approval')

        return (user, token)

    def authenticate_header(self, request):
        """
        Bearer is the only finalized type currently

        Check details on the `OAuth2Authentication.authenticate` method
        """
        return 'Bearer realm="%s"' % self.www_authenticate_realm


'''
We also overwrite TokenAuthentication so we can add extra features and change the default Token model.
'''


class TokenAuthentication(BaseAuthentication):
    """
    Simple token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Token ".  For example:

        Authorization: Token 401f7ac837da42b97f613d789819ff93537bee6a
    """

    model = ApiV2Client

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'token':
            return None

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(auth[1])

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        if not token.status == 'OK':
            raise exceptions.AuthenticationFailed('Suspended token or token pending for approval')

        return (token.user, token)

    def authenticate_header(self, request):
        return 'Token'