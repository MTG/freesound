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

from django.urls import include, path, re_path
from django.contrib.auth.views import LogoutView
from apiv2 import views
from accounts.views import login
from accounts.forms import FsAuthenticationForm

#
# WATCH OUT! if changing url pattern names these should be changed in views __doc__ too (to make sure examples work properly)
#

urlpatterns = [
    #############
    # READ ONLY #
    #############
    # Me
    path("me/", views.Me.as_view(), name="apiv2-me"),
    path("me/bookmark_categories/", views.MeBookmarkCategories.as_view(), name="apiv2-me-bookmark-categories"),
    path(
        "me/bookmark_categories/<int:category_id>/sounds/",
        views.MeBookmarkCategorySounds.as_view(),
        name="apiv2-me-bookmark-category-sounds",
    ),
    # Text/content/combined search
    path("search/", views.TextSearch.as_view(), name="apiv2-sound-search"),
    path("search/text/", views.TextSearch.as_view(), name="apiv2-sound-text-search"),
    path("search/content/", views.ContentSearch.as_view(), name="apiv2-sound-content-search"),
    path("search/combined/", views.CombinedSearch.as_view(), name="apiv2-sound-combined-search"),
    # Sounds
    path("sounds/<int:pk>/", views.SoundInstance.as_view(), name="apiv2-sound-instance"),
    path("sounds/<int:pk>/comments/", views.SoundComments.as_view(), name="apiv2-sound-comments"),
    path("sounds/<int:pk>/analysis/", views.SoundAnalysisView.as_view(), name="apiv2-sound-analysis"),
    path("sounds/<int:pk>/similar/", views.SimilarSounds.as_view(), name="apiv2-similarity-sound"),
    path("sounds/<int:pk>/download/", views.DownloadSound.as_view(), name="apiv2-sound-download"),
    path("sounds/<int:pk>/download/link/", views.DownloadLink.as_view(), name="apiv2-sound-get-download-link"),
    # Create or edit
    path("sounds/<int:pk>/edit/", views.EditSoundDescription.as_view(), name="apiv2-sound-edit"),
    path("sounds/<int:pk>/bookmark/", views.BookmarkSound.as_view(), name="apiv2-user-create-bookmark"),
    path("sounds/<int:pk>/rate/", views.RateSound.as_view(), name="apiv2-user-create-rating"),
    path("sounds/<int:pk>/comment/", views.CommentSound.as_view(), name="apiv2-user-create-comment"),
    # Upload and describe
    path("sounds/upload/", views.UploadSound.as_view(), name="apiv2-uploads-upload"),
    path("sounds/describe/", views.DescribeSound.as_view(), name="apiv2-uploads-describe"),
    path("sounds/pending_uploads/", views.PendingUploads.as_view(), name="apiv2-uploads-pending"),
    # Users
    path("users/<username>/", views.UserInstance.as_view(), name="apiv2-user-instance"),
    path("users/<username>/sounds/", views.UserSounds.as_view(), name="apiv2-user-sound-list"),
    path("users/<username>/packs/", views.UserPacks.as_view(), name="apiv2-user-packs"),
    # Packs
    path("packs/<int:pk>/", views.PackInstance.as_view(), name="apiv2-pack-instance"),
    path("packs/<int:pk>/sounds/", views.PackSounds.as_view(), name="apiv2-pack-sound-list"),
    path("packs/<int:pk>/download/", views.DownloadPack.as_view(), name="apiv2-pack-download"),
    # Download item from link
    path("download/<token>/", views.download_from_token, name="apiv2-download_from_token"),
    #########################
    # MANAGEMENT AND OAUTH2 #
    #########################
    # Client management
    # use apply[/]* for backwards compatibility with links to /apiv2/apply
    re_path(r"^apply[/]*$", views.create_apiv2_key, name="apiv2-apply"),
    re_path(
        r"^apply/credentials/(?P<key>[^//]+)/monitor/$", views.monitor_api_credential, name="apiv2-monitor-credential"
    ),
    re_path(
        r"^apply/credentials/(?P<key>[^//]+)/delete/$", views.delete_api_credential, name="apiv2-delete-credential"
    ),
    re_path(r"^apply/credentials/(?P<key>[^//]+)/edit/$", views.edit_api_credential, name="apiv2-edit-credential"),
    # Oauth2
    path("oauth2/", include("apiv2.oauth2_urls", namespace="oauth2_provider")),
    path(
        "login/",
        login,
        {"template_name": "oauth2_provider/oauth_login.html", "authentication_form": FsAuthenticationForm},
        name="api-login",
    ),
    path("logout/", LogoutView.as_view(next_page="/apiv2/"), name="api-logout"),
    #########
    # OTHER #
    #########
    path("", views.FreesoundApiV2Resources.as_view()),
    path("/", views.invalid_url),
]
