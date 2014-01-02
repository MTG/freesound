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
    url(r'^search/combined/$', views.CombinedSearch.as_view(), name="apiv2-sound-combined-search"),
    url(r'^search/target_file/$', views.SimilarityFile.as_view(), name="apiv2-similarity-file"),

    # Sounds
    url(r'^sounds/(?P<pk>[0-9]+)/$', views.SoundInstance.as_view(), name="apiv2-sound-instance"),
    url(r'^sounds/(?P<pk>[0-9]+)/ratings/$', views.SoundRatings.as_view(), name="apiv2-sound-ratings"),
    url(r'^sounds/(?P<pk>[0-9]+)/comments/$', views.SoundComments.as_view(), name="apiv2-sound-comments"),
    url(r'^sounds/(?P<pk>[0-9]+)/analysis/$', views.SoundAnalysis.as_view(), name="apiv2-sound-analysis"),
    url(r'^sounds/(?P<pk>[0-9]+)/similar/$', views.SimilaritySound.as_view(), name="apiv2-similarity-sound"),
    url(r'^sounds/list_from_ids/$', views.SoundListFromIds.as_view(), name="apiv2-sound-list-from-ids"),
    url(r'^sounds/(?P<pk>[0-9]+)/download/$', views.SoundDownload.as_view(), name="apiv2-sound-download"),

    # Users
    url(r'^users/(?P<username>[^//]+)/$', views.UserInstance.as_view(), name="apiv2-user-instance"),
    url(r'^users/(?P<username>[^//]+)/sounds/$', views.UserSoundList.as_view(), name="apiv2-user-sound-list"),
    url(r'^users/(?P<username>[^//]+)/packs/$', views.UserPacks.as_view(), name='apiv2-user-packs'),
    url(r'^users/(?P<username>[^//]+)/bookmarks/$', views.UserBookmarks.as_view(), name='apiv2-user-bookmark-categories'),
    url(r'^users/(?P<username>[^//]+)/bookmarks/category/uncategorized/sounds/$', views.UserBookmarkSounds.as_view(),    name='apiv2-user-bookmark-uncategorized'),
    url(r'^users/(?P<username>[^//]+)/bookmarks/category/(?P<category_id>\d+)/sounds/$', views.UserBookmarkSounds.as_view(), name='apiv2-user-bookmark-category-sounds'),

    # Packs
    url(r'^packs/(?P<pk>[0-9]+)/$', views.PackInstance.as_view(), name='apiv2-pack-instance'),
    url(r'^packs/(?P<pk>[0-9]+)/sounds/$', views.PackSoundList.as_view(), name='apiv2-pack-sound-list'),
    url(r'^packs/(?P<pk>[0-9]+)/download/$', views.PackDownload.as_view(), name='apiv2-pack-download'),


    ##############
    # READ WRITE #
    ##############

    # Upload sounds
    url(r'^post/sound/$', views.UploadAudioFile.as_view(), name="apiv2-uploads-upload"),
    url(r'^post/sound/not_yet_described/$', views.NotYetDescribedUploadedAudioFiles.as_view(), name="apiv2-uploads-not-described"),
    url(r'^post/sound/describe/$', views.DescribeAudioFile.as_view(), name="apiv2-uploads-describe"),
    url(r'^post/sound/upload_and_describe/$', views.UploadAndDescribeAudioFile.as_view(), name="apiv2-uploads-upload-and-describe"),

    # Other
    url(r'^post/bookmark/$', views.CreateBookmark.as_view(), name='apiv2-user-create-bookmark'),
    url(r'^post/rating/$', views.CreateRating.as_view(), name='apiv2-user-create-rating'),
    url(r'^post/comment/$', views.CreateComment.as_view(), name='apiv2-user-create-comment'),


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

    url(r'^$', 'api_root'),
    url(r'/$', views.return_invalid_url),
)


