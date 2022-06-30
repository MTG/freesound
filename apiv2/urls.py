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


from django.conf.urls import url, include
from django.contrib.auth.views import LoginView, LogoutView
from apiv2 import views
from accounts.views import login
from accounts.forms import FsAuthenticationForm

#
# WATCH OUT! if changing url pattern names these should be changed in vews __doc__ too (to make sure examples work properly)
#

urlpatterns = [
    #############
    # READ ONLY #
    #############

    # Me
    url(r'^me/$', views.Me.as_view(), name="apiv2-me"),

    # Available audio descriptors
    url(r'^descriptors/$', views.AvailableAudioDescriptors.as_view(), name="apiv2-available-descriptors"),

    # Text/content/combined search
    url(r'^search/text/$', views.TextSearch.as_view(), name="apiv2-sound-text-search"),
    url(r'^search/content/$', views.ContentSearch.as_view(), name="apiv2-sound-content-search"),
    url(r'^search/combined/$', views.CombinedSearch.as_view(), name="apiv2-sound-combined-search"),

    # Sounds
    url(r'^sounds/(?P<pk>[0-9]+)/$', views.SoundInstance.as_view(), name="apiv2-sound-instance"),
    url(r'^sounds/(?P<pk>[0-9]+)/comments/$', views.SoundComments.as_view(), name="apiv2-sound-comments"),
    url(r'^sounds/(?P<pk>[0-9]+)/analysis/$', views.SoundAnalysisView.as_view(), name="apiv2-sound-analysis"),
    url(r'^sounds/(?P<pk>[0-9]+)/similar/$', views.SimilarSounds.as_view(), name="apiv2-similarity-sound"),
    url(r'^sounds/(?P<pk>[0-9]+)/download/$', views.DownloadSound.as_view(), name="apiv2-sound-download"),
    url(r'^sounds/(?P<pk>[0-9]+)/download/link/$', views.DownloadLink.as_view(), name="apiv2-sound-get-download-link"),

    # Create or edit
    url(r'^sounds/(?P<pk>[0-9]+)/edit/$', views.EditSoundDescription.as_view(), name='apiv2-sound-edit'),
    url(r'^sounds/(?P<pk>[0-9]+)/bookmark/$', views.BookmarkSound.as_view(), name='apiv2-user-create-bookmark'),
    url(r'^sounds/(?P<pk>[0-9]+)/rate/$', views.RateSound.as_view(), name='apiv2-user-create-rating'),
    url(r'^sounds/(?P<pk>[0-9]+)/comment/$', views.CommentSound.as_view(), name='apiv2-user-create-comment'),
    # Upload and describe
    url(r'^sounds/upload/$', views.UploadSound.as_view(), name="apiv2-uploads-upload"),
    url(r'^sounds/describe/$', views.DescribeSound.as_view(), name="apiv2-uploads-describe"),
    url(r'^sounds/pending_uploads/$', views.PendingUploads.as_view(), name="apiv2-uploads-pending"),

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

    # Download item from link
    url(r'^download/(?P<token>.+?)/$', views.download_from_token, name="apiv2-download_from_token"),


    #########################
    # MANAGEMENT AND OAUTH2 #
    #########################

    # Client management
    # use apply[/]* for backwards compatibility with links to /apiv2/apply
    url(r'^apply[/]*$', views.create_apiv2_key, name="apiv2-apply"),
    url(r'^apply/credentials/(?P<key>[^//]+)/monitor/$', views.monitor_api_credential, name="apiv2-monitor-credential"),
    url(r'^apply/credentials/(?P<key>[^//]+)/delete/$', views.delete_api_credential, name="apiv2-delete-credential"),
    url(r'^apply/credentials/(?P<key>[^//]+)/edit/$', views.edit_api_credential, name="apiv2-edit-credential"),

    # Oauth2
    url(r'^oauth2/', include('apiv2.oauth2_urls', namespace='oauth2_provider')),
    url(r'^login/$', login, {'template_name': 'api/minimal_login.html',
                             'authentication_form': FsAuthenticationForm}, name="api-login"),
    url(r'^logout/$', LogoutView.as_view(next_page='/apiv2/'), name="api-logout"),

    #########
    # OTHER #
    #########
    url(r'^$', views.FreesoundApiV2Resources.as_view()),
    url(r'/$', views.invalid_url),
]


