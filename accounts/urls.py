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

from django.conf.urls import url
from django.contrib.auth import views as auth_views
from utils.session_checks import login_redirect
import messages.views as messages
import accounts.views as accounts
from accounts.forms import FsAuthenticationForm, FsPasswordResetForm
import bookmarks.views as bookmarks
import follow.views as follow
import apiv2.views as api
from utils.frontend_handling import redirect_if_beastwhoosh_inline

# By putting some URLs at the top that are the same as the ones listed in
# django.contrib.auth.urls, we can override some configuration:
# https://docs.djangoproject.com/en/1.11/topics/http/urls/#how-django-processes-a-request
# 3. Django runs through each URL pattern, in order, and stops at the first one that matches the requested URL.
urlpatterns = [
    url(r'^login/$', login_redirect(accounts.login), {'template_name': 'registration/login.html',
                                       'authentication_form': FsAuthenticationForm}, name="login"),
    url(r'^logout/$', auth_views.LogoutView.as_view(), name='logout'),
    url(r'^cleanup/$', accounts.multi_email_cleanup, name="accounts-multi-email-cleanup"),
    url(r'^password_reset/$',
        login_redirect(
            redirect_if_beastwhoosh_inline(
                auth_views.PasswordResetView.as_view(form_class=FsPasswordResetForm),
                redirect_url_name='front-page',
                query_string='loginProblems=1')),
        name='password_reset'),
    url(r'^password_reset/done/$',
        redirect_if_beastwhoosh_inline(
            auth_views.PasswordResetDoneView.as_view(),
            redirect_url_name='front-page'),
        name='password_reset_done'),
    url(r'^password_change/$', accounts.password_change_form, name='password_change'),
    url(r'^password_change/done/$', accounts.password_change_done, name='password_change_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        accounts.password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/done/$', accounts.password_reset_complete, name='password_reset_complete'),
    url(r'^register/$', login_redirect(accounts.registration), name="accounts-register"),
    url(r'^reactivate/$', login_redirect(accounts.resend_activation), name="accounts-resend-activation"),
    url(r'^username/$', login_redirect(accounts.username_reminder), name="accounts-username-reminder"),
    url(r'^activate/(?P<username>[^\/]+)/(?P<uid_hash>[^\/]+)/.*$', login_redirect(accounts.activate_user), name="accounts-activate"),
    url(r'^resetemail/$', accounts.email_reset, name="accounts-email-reset"),
    url(r'^resetemail/sent/$', accounts.email_reset_done, name="accounts-email-reset-done"),
    url(r'^resetemail/complete/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', accounts.email_reset_complete, name="accounts-email-reset-complete"),
    url(r'^problems/$', accounts.problems_logging_in, name="problems-logging-in"),
    url(r'^bulklicensechange/$', accounts.bulk_license_change, name="bulk-license-change"),
    url(r'^tosacceptance/$', accounts.tos_acceptance, name="tos-acceptance"),
    url(r'^check_username/$', accounts.check_username, name="check_username"),
    url(r'^update_old_cc_licenses/$', accounts.update_old_cc_licenses, name="update-old-cc-licenses"),

    url(r'^$', accounts.home, name="accounts-home"),
    url(r'^edit/$', accounts.edit, name="accounts-edit"),
    url(r'^email-settings/$', accounts.edit_email_settings, name="accounts-email-settings"),
    url(r'^delete/$', accounts.delete, name="accounts-delete"),
    url(r'^pending/$', accounts.pending, name="accounts-pending"),
    url(r'^attribution/$', accounts.attribution, name="accounts-attribution"),
    url(r'^download-attribution/$', accounts.download_attribution, name="accounts-download-attribution"),
    url(r'^stream/$', follow.stream, name='stream'),

    url(r'^upload/$', accounts.upload, name="accounts-upload", kwargs=dict(no_flash=True)),
    url(r'^upload/html/$', accounts.upload, name="accounts-upload-html", kwargs=dict(no_flash=True)),
    url(r'^upload/flash/$', accounts.upload, name="accounts-upload-flash"),
    url(r'^upload/file/$', accounts.upload_file, name="accounts-upload-file"),
    url(r'^upload/bulk-describe/(?P<bulk_id>[0-9]+)/$', accounts.bulk_describe, name="accounts-bulk-describe"),

    url(r'^describe/$', accounts.describe, name="accounts-describe"),
    url(r'^describe/license/$', accounts.describe_license, name="accounts-describe-license"),
    url(r'^describe/pack/', accounts.describe_pack, name="accounts-describe-pack"),
    url(r'^describe/sounds/', accounts.describe_sounds, name="accounts-describe-sounds"),

    url(r'^bookmarks/$', bookmarks.bookmarks, name="bookmarks"),
    url(r'^bookmarks/category/(?P<category_id>\d+)/$', bookmarks.bookmarks, name="bookmarks-category"),
    url(r'^bookmarks/add/(?P<sound_id>\d+)/$', bookmarks.add_bookmark, name="add-bookmark"),
    url(r'^bookmarks/get_form_for_sound/(?P<sound_id>\d+)/$', bookmarks.get_form_for_sound, name="bookmarks-add-form-for-sound"),
    url(r'^bookmarks/category/(?P<category_id>\d+)/delete/$', bookmarks.delete_bookmark_category, name="delete-bookmark-category"),
    url(r'^bookmarks/(?P<bookmark_id>\d+)/delete/$', bookmarks.delete_bookmark, name="delete-bookmark"),

    url(r'^messages/$', messages.inbox, name='messages'),
    url(r'^messages/sent/$', messages.sent_messages, name='messages-sent'),
    url(r'^messages/archived/$', messages.archived_messages, name='messages-archived'),
    url(r'^messages/changestate/$', messages.messages_change_state, name='messages-change-state'),
    url(r'^messages/(?P<message_id>\d+)/$', messages.message, name='message'),
    url(r'^messages/(?P<message_id>\d+)/reply/$', messages.new_message, name='message-reply', kwargs=dict(username=None)),
    url(r'^messages/new/$', messages.new_message, name='messages-new'),
    url(r'^messages/new/(?P<username>[^//]+)/$', messages.new_message, name='messages-new', kwargs=dict(message_id=None)),
    url(r'^messages/new/username_lookup$', messages.username_lookup, name='messages-username_lookup'),

    url(r'^app_permissions/$', api.granted_permissions, name='access-tokens'),
    url(r'^app_permissions/revoke_permission/(?P<client_id>[^//]+)/$', api.revoke_permission, name='revoke-permission'),
    url(r'^app_permissions/permission_granted/$', api.permission_granted, name='permission-granted'),
]
