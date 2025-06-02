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

from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from utils.session_checks import login_redirect
import messages.views as messages
import accounts.views as accounts
from accounts.forms import FsAuthenticationForm, FsPasswordResetForm
import bookmarks.views as bookmarks
import follow.views as follow
import apiv2.views as api
from utils.url import redirect_inline



# By putting some URLs at the top that are the same as the ones listed in
# django.contrib.auth.urls, we can override some configuration:
# https://docs.djangoproject.com/en/1.11/topics/http/urls/#how-django-processes-a-request
# 3. Django runs through each URL pattern, in order, and stops at the first one that matches the requested URL.
urlpatterns = [
    path('login/', login_redirect(accounts.login), {'template_name': 'registration/login.html',
                                       'authentication_form': FsAuthenticationForm}, name="login"),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('cleanup/', accounts.multi_email_cleanup, name="accounts-multi-email-cleanup"),
    path('password_reset/',
        login_redirect(
            redirect_inline(
                auth_views.PasswordResetView.as_view(form_class=FsPasswordResetForm),
                redirect_url_name='front-page',
                query_string='loginProblems=1')),
        name='password_reset'),
    path('password_reset/done/',
        redirect_inline(
            auth_views.PasswordResetDoneView.as_view(),
            redirect_url_name='front-page'),
        name='password_reset_done'),
    path('password_change/', accounts.password_change_form, name='password_change'),
    path('password_change/done/', accounts.password_change_done, name='password_change_done'),
    path('reset/<uidb64>/<token>/', accounts.password_reset_confirm, name='password_reset_confirm'),
    path('reset/done/', accounts.password_reset_complete, name='password_reset_complete'),
    path('registration_modal/', login_redirect(accounts.registration_modal), name="accounts-registration-modal"),
    path('reactivate/', login_redirect(accounts.resend_activation), name="accounts-resend-activation"),
    path('username/', login_redirect(accounts.username_reminder), name="accounts-username-reminder"),
    re_path(r'^activate/(?P<username>[^\/]+)/(?P<uid_hash>[^\/]+)/.*$', login_redirect(accounts.activate_user), name="accounts-activate"),
    path('resetemail/', accounts.email_reset, name="accounts-email-reset"),
    path('resetemail/sent/', accounts.email_reset_done, name="accounts-email-reset-done"),
    re_path(r'^resetemail/complete/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', accounts.email_reset_complete, name="accounts-email-reset-complete"),
    path('problems/', accounts.problems_logging_in, name="problems-logging-in"),
    path('bulklicensechange/', accounts.bulk_license_change, name="bulk-license-change"),
    path('tosacceptance/', accounts.tos_acceptance, name="tos-acceptance"),
    path('check_username/', accounts.check_username, name="check_username"),
    path('update_old_cc_licenses/', accounts.update_old_cc_licenses, name="update-old-cc-licenses"),

    path('', accounts.home, name="accounts-home"),
    path('edit/', accounts.edit, name="accounts-edit"),
    path('email-settings/', accounts.edit_email_settings, name="accounts-email-settings"),
    path('delete/', accounts.delete, name="accounts-delete"),
    path('attribution/', accounts.attribution, name="accounts-attribution"),
    path('download-attribution/', accounts.download_attribution, name="accounts-download-attribution"),
    path('stream/', follow.stream, name='stream'),

    path('upload/', accounts.upload, name="accounts-upload"),
    path('upload/bulk-describe/<int:bulk_id>/', accounts.bulk_describe, name="accounts-bulk-describe"),

    path('sounds/manage/<tab>/', accounts.manage_sounds, name="accounts-manage-sounds"),
    path('sounds/edit/', accounts.edit_sounds, name="accounts-edit-sounds"),
    path('describe/license/', accounts.describe_license, name="accounts-describe-license"),
    path('describe/pack/', accounts.describe_pack, name="accounts-describe-pack"),
    path('describe/sounds/', accounts.describe_sounds, name="accounts-describe-sounds"),
    
    path('bookmarks/', bookmarks.bookmarks, name="bookmarks"),
    path('bookmarks/category/<int:category_id>/', bookmarks.bookmarks, name="bookmarks-category"),
    path('bookmarks/add/<int:sound_id>/', bookmarks.add_bookmark, name="add-bookmark"),
    path('bookmarks/get_form_for_sound/<int:sound_id>/', bookmarks.get_form_for_sound, name="bookmarks-add-form-for-sound"),
    path('bookmarks/category/<int:category_id>/delete/', bookmarks.delete_bookmark_category, name="delete-bookmark-category"),
    path('bookmarks/<int:bookmark_id>/delete/', bookmarks.delete_bookmark, name="delete-bookmark"),
    path('bookmarks/category/<int:category_id>/edit_modal/', bookmarks.edit_bookmark_category, name="edit-bookmark-category"),
    path('bookmarks/category/<int:category_id>/download/', bookmarks.download_bookmark_category, name="download-bookmark-category"),
    path('bookmarks/category/<int:category_id>/licenses/', bookmarks.bookmark_category_licenses, name="category-licenses"),

    path('messages/', messages.inbox, name='messages'),
    path('messages/sent/', messages.sent_messages, name='messages-sent'),
    path('messages/archived/', messages.archived_messages, name='messages-archived'),
    path('messages/changestate/', messages.messages_change_state, name='messages-change-state'),
    path('messages/<int:message_id>/', messages.message, name='message'),
    path('messages/<int:message_id>/reply/', messages.new_message, name='message-reply', kwargs=dict(username=None)),
    path('messages/new/', messages.new_message, name='messages-new'),
    path('messages/new/<username>/', messages.new_message, name='messages-new', kwargs=dict(message_id=None)),
    path('messages/new/username_lookup', messages.username_lookup, name='messages-username_lookup'),

    path('app_permissions/', api.granted_permissions, name='access-tokens'),
    path('app_permissions/revoke_permission/<client_id>/', api.revoke_permission, name='revoke-permission'),
    path('app_permissions/permission_granted/', api.permission_granted, name='permission-granted'),
]
