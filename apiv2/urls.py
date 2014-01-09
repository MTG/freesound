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
    #############
    # READ ONLY #
    #############

    # Me
    url(r'^me/$', views.Me.as_view(), name="apiv2-me"),

    # Search and similarity search
    url(r'^search/$', views.Search.as_view(), name="apiv2-sound-search"),
    url(r'^search/advanced/$', views.AdvancedSearch.as_view(), name="apiv2-sound-combined-search"),

    # Sounds
    url(r'^sounds/(?P<pk>[0-9]+)/$', views.SoundInstance.as_view(), name="apiv2-sound-instance"),
    url(r'^sounds/(?P<pk>[0-9]+)/comments/$', views.SoundComments.as_view(), name="apiv2-sound-comments"),
    url(r'^sounds/(?P<pk>[0-9]+)/analysis/$', views.SoundAnalysis.as_view(), name="apiv2-sound-analysis"),
    url(r'^sounds/(?P<pk>[0-9]+)/similar/$', views.SimilarSounds.as_view(), name="apiv2-similarity-sound"),
    url(r'^sounds/(?P<pk>[0-9]+)/download/$', views.DownloadSound.as_view(), name="apiv2-sound-download"),
    # Create
    url(r'^sounds/(?P<pk>[0-9]+)/bookmark/$', views.BookmarkSound.as_view(), name='apiv2-user-create-bookmark'),
    url(r'^sounds/(?P<pk>[0-9]+)/rate/$', views.RateSound.as_view(), name='apiv2-user-create-rating'),
    url(r'^sounds/(?P<pk>[0-9]+)/comment/$', views.CommentSound.as_view(), name='apiv2-user-create-comment'),
    # Upload
    url(r'^sounds/upload/$', views.UploadSound.as_view(), name="apiv2-uploads-upload"),
    url(r'^sounds/not_yet_described/$', views.NotYetDescribedUploadedSounds.as_view(), name="apiv2-uploads-not-described"),
    url(r'^sounds/describe/$', views.DescribeSound.as_view(), name="apiv2-uploads-describe"),
    url(r'^sounds/upload_and_describe/$', views.UploadAndDescribeSound.as_view(), name="apiv2-uploads-upload-and-describe"),

    # Users
    url(r'^users/(?P<username>[^//]+)/$', views.UserInstance.as_view(), name="apiv2-user-instance"),
    url(r'^users/(?P<username>[^//]+)/sounds/$', views.UserSounds.as_view(), name="apiv2-user-sound-list"),
    url(r'^users/(?P<username>[^//]+)/packs/$', views.UserPacks.as_view(), name='apiv2-user-packs'),
    url(r'^users/(?P<username>[^//]+)/bookmark_categories/$', views.UserBookmarkCategories.as_view(), name='apiv2-user-bookmark-categories'),
    url(r'^users/(?P<username>[^//]+)/bookmark_categories/(?P<category_id>\d+)/sounds/$', views.UserBookmarkCategorySounds.as_view(), name='apiv2-user-bookmark-category-sounds'),

    # Packs
    url(r'^packs/(?P<pk>[0-9]+)/$', views.PackInstance.as_view(), name='apiv2-pack-instance'),
    url(r'^packs/(?P<pk>[0-9]+)/sounds/$', views.PackSounds.as_view(), name='apiv2-pack-sound-list'),
    url(r'^packs/(?P<pk>[0-9]+)/download/$', views.DownloadPack.as_view(), name='apiv2-pack-download'),


    #########################
    # MANAGEMENT AND OAUTH2 #
    #########################

    # Client management
    url(r'^apply/$', views.create_apiv2_key, name="apiv2-apply"),
    url(r'^apply/credentials/(?P<key>[^//]+)/delete/$', views.delete_api_credential, name="apiv2-delete-credential"),
    url(r'^apply/credentials/(?P<key>[^//]+)/edit/$', views.edit_api_credential, name="apiv2-edit-credential"),

    # Oauth2
    url(r'^oauth2/', include('apiv2.oauth2_urls', namespace='oauth2')),
    url(r'^login/$', login, {'template_name': 'api/minimal_login.html'}, name="api-login"),


    #########
    # OTHER #
    #########

    url(r'^$', views.FreesoundApiV2Resources.as_view()),
    url(r'/$', views.return_invalid_url),
)


