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
    url(r'^$', 'api_root'),

    # Sounds
    url(r'^sounds/(?P<pk>[0-9]+)/$', views.SoundInstance.as_view(), name="apiv2-sound-instance"),
    url(r'^sounds/search/$', views.SoundSearch.as_view(), name="apiv2-sound-search"),
    url(r'^sounds/combined_search/$', views.SoundCombinedSearch.as_view(), name="apiv2-sound-advanced-search"),

    # Users
    url(r'^users/(?P<username>[^//]+)/$', views.UserInstance.as_view(), name="apiv2-user-instance"),
    url(r'^users/(?P<username>[^//]+)/sounds/$', views.UserSoundList.as_view(), name="apiv2-user-sound-list"),

    # Packs
    url(r'^packs/(?P<pk>[0-9]+)/$', views.PackInstance.as_view(), name='apiv2-pack-instance'),
    url(r'^packs/(?P<pk>[0-9]+)/sounds/$', views.PackSoundList.as_view(), name='apiv2-pack-sound-list'),

    # Upload files
    url(r'^uploads/upload/$', views.UploadAudioFile.as_view(), name="apiv2-uploads-upload"),
    url(r'^uploads/not_yet_described/$', views.NotYetDescribedUploadedAudioFiles.as_view(), name="apiv2-uploads-not-described"),
    url(r'^uploads/describe/$', views.DescribeAudioFile.as_view(), name="apiv2-uploads-describe"),
    url(r'^uploads/upload_and_describe/$', views.UploadAndDescribeAudioFile.as_view(), name="apiv2-uploads-upload-and-describe"),

    # Client management
    url(r'^apply/$', views.create_apiv2_key, name="apiv2-apply"),
    url(r'^apply/credentials/(?P<key>[^//]+)/delete/$', views.delete_api_credential, name="apiv2-delete-credential"),
    url(r'^apply/credentials/(?P<key>[^//]+)/edit/$', views.edit_api_credential, name="apiv2-edit-credential"),

    # Include views for three-legged auth process
    url(r'^oauth2/', include('apiv2.oauth2_urls', namespace='oauth2')),
    url(r'^login/$', login, {'template_name': 'api/minimal_login.html'}, name="api-login"),

    # Any other url
    url(r'/$', views.return_invalid_url),

)


