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

# packages to install:
#   - django-oauth2-provider ('0.2.6')
#   - djangorestframework ('2.3.8')
#   - markdown (for browseable api)


from django.conf.urls.defaults import patterns, url, include
from django.contrib.auth.views import login
from apiv2 import views


urlpatterns = patterns('apiv2.views',
       url(r'^apply/$', views.create_apiv2_key),
       url(r'^$', 'api_root'),
       #    url(r'^sounds/$', views.SoundList.as_view(), name="sound-list"),
       url(r'^sounds/(?P<pk>[0-9]+)/$', views.SoundDetail.as_view(), name="apiv2-sound-detail"),
       url(r'^users/(?P<pk>[0-9]+)/$', views.UserDetail.as_view(), name="apiv2-user-detail"),
       url(r'^users/(?P<pk>[0-9]+)/sounds/$', views.UserSoundList.as_view(), name="apiv2-user-sound-list"),

       # Include views for three-legged auth process
       url(r'^oauth2/', include('apiv2.oauth2_urls', namespace='oauth2')),
       url(r'^login/$', login, {'template_name': 'api/minimal_login.html'}, name="api-login"),

       # Any other url
       url(r'/$', views.return_invalid_url ),
)


