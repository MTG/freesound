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

from apiv2.views import AuthorizationView
from oauth2_provider import views
from django.urls import re_path
from django.conf import settings
from django.contrib.auth import logout, REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.urls import reverse


def https_required(view_func):

    def _wrapped_view_func(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return HttpResponse('{"detail": "This resource requires a secure connection (https)"}', status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped_view_func


def force_login(view_func):

    def _wrapped_view_func(request, *args, **kwargs):
        logout(request)
        path = request.build_absolute_uri()
        path = path.replace('logout_and_', '')    # To avoid loop in this view
        return redirect_to_login(path, reverse('api-login'), REDIRECT_FIELD_NAME)

    return _wrapped_view_func


app_name = 'oauth2_provider'

urlpatterns = (
    re_path(r'^authorize[/]*$', https_required(AuthorizationView.as_view()), name="authorize"),
    re_path(
        r'^logout_and_authorize[/]*$',
        https_required(force_login(AuthorizationView.as_view())),
        name="logout_and_authorize"
    ),
    re_path(r'^access_token[/]*$', csrf_exempt(https_required(views.TokenView.as_view())), name="access_token"),
)
