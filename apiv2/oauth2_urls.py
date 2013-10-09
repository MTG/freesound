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

from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from provider.oauth2.views import Redirect, Capture
from apiv2.utils import AccessTokenView, Authorize

'''
We create oauth2_urls.py files and then include to the main apiv2/urls.py because we were having namespace problems
otherwise. Apparently if namespace is defined manually (ex: name='oauth2:capture'), Django complains.
'''

urlpatterns = patterns('',
    url('^authorize/?$', login_required(Capture.as_view()), name='capture'),
    url('^authorize/confirm/?$', login_required(Authorize.as_view()), name='authorize'),
    url('^redirect/?$', login_required(Redirect.as_view()), name='redirect'),
    url('^access_token/?$', csrf_exempt(AccessTokenView.as_view()), name='access_token'),
)

