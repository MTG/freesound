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

#from __future__ import absolute_import
'''
from django.conf.urls import patterns, url
from django.contrib.auth import logout
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from apiv2.apiv2_utils import AccessTokenView, Authorize, Capture, Redirect, prepend_base
from django.conf import settings
'''

'''
We create oauth2_urls.py files and then include to the main apiv2/urls.py because we were having namespace problems
otherwise. Apparently if namespace is defined manually (ex: name='oauth2:capture'), Django complains.
'''
'''

if settings.USE_MINIMAL_TEMPLATES_FOR_OAUTH:
    login_url = prepend_base('/apiv2/login/', use_https=not settings.DEBUG, dynamic_resolve=False)
else:
    login_url = prepend_base(settings.LOGIN_URL, use_https=not settings.DEBUG, dynamic_resolve=False)


def https_and_login_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return HttpResponse('{"detail": "This resource requires a secure connection (https)"}', status=403)
        if not request.user.is_authenticated():
            # Quick fix, should be implemented better
            path = request.build_absolute_uri().split('/apiv2/')[1]
            path = prepend_base('/apiv2/' + path, use_https=not settings.DEBUG, dynamic_resolve=False)
            return redirect_to_login(path, login_url, REDIRECT_FIELD_NAME)

        return view_func(request, *args, **kwargs)
    return _wrapped_view_func
    #return login_required(_wrapped_view_func, login_url=login_url)

def https_and_force_login(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return HttpResponse('{"detail": "This resource requires a secure connection (https)"}', status=403)
        # Logout the user so we make sure he needs to login again
        logout(request)
        # Quick fix, should be implemented better
        path = request.build_absolute_uri().split('/apiv2/')[1]
        path = prepend_base('/apiv2/' + path, use_https=not settings.DEBUG, dynamic_resolve=False)
        path = path.replace('logout_and_', '')
        return redirect_to_login(path, login_url, REDIRECT_FIELD_NAME)

    return _wrapped_view_func
    #return login_required(_wrapped_view_func, login_url=login_url)


def https_required_and_crsf_exempt(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return HttpResponse('{"detail": "This resource requires a secure connection (https)"}', status=403)
        return view_func(request, *args, **kwargs)
    return csrf_exempt(_wrapped_view_func)


urlpatterns = patterns('',
    url('^authorize/?$', https_and_login_required(Capture.as_view()), name='capture'),
    url('^logout_and_authorize/?$', https_and_force_login(Capture.as_view()), name='capture'),
    url('^authorize/confirm/?$', https_and_login_required(Authorize.as_view()), name='authorize'),
    url('^redirect/?$', https_and_login_required(Redirect.as_view()), name='redirect'),
    url('^access_token/?$', https_required_and_crsf_exempt(AccessTokenView.as_view()), name='access_token'),
)
'''

from django.conf.urls import url
from apiv2.views import AuthorizationView
from oauth2_provider import views

urlpatterns = (
    url(r'^authorize/$', AuthorizationView.as_view(), name="authorize"),
    url(r'^access_token/$', views.TokenView.as_view(), name="access_token"),
    url(r'^revoke_token/$', views.RevokeTokenView.as_view(), name="revoke-token"),
)

# Application management views
urlpatterns += (
    url(r'^applications/$', views.ApplicationList.as_view(), name="list"),
    url(r'^applications/register/$', views.ApplicationRegistration.as_view(), name="register"),
    url(r'^applications/(?P<pk>\d+)/$', views.ApplicationDetail.as_view(), name="detail"),
    url(r'^applications/(?P<pk>\d+)/delete/$', views.ApplicationDelete.as_view(), name="delete"),
    url(r'^applications/(?P<pk>\d+)/update/$', views.ApplicationUpdate.as_view(), name="update"),
)

urlpatterns += (
    url(r'^authorized_tokens/$', views.AuthorizedTokensListView.as_view(), name="authorized-token-list"),
    url(r'^authorized_tokens/(?P<pk>\d+)/delete/$', views.AuthorizedTokenDeleteView.as_view(),
        name="authorized-token-delete"),
)
