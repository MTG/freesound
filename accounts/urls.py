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
import django.contrib.auth.views as authviews
import messages.views as messages
import accounts.views as accounts
import bookmarks.views as bookmarks

urlpatterns = patterns('accounts.views',

    url(r'^login/$',
        accounts.login_wrapper,
        name="accounts-login"),

    url(r'^logout/$',
        authviews.logout,
        {'template_name': 'accounts/logout.html'},
        name="accounts-logout"),

    url(r'^reactivate/$',
        accounts.resend_activation,
        name="accounts-resend-activation"),

    url(r'^username/$',
        accounts.username_reminder,
        name="accounts-username-reminder"),

    url(r'^activate/(?P<activation_key>[^//]+)/(?P<username>\w+)/$',
        accounts.activate_user,
        name="accounts-activate"),

    url(r'^activate2/(?P<username>[^\/]+)/(?P<hash>[^\/]+)/.*$', # old pattern: url(r'^activate2/(?P<username>[^\/]+)/(?P<hash>[^\/]+)/$',
        accounts.activate_user2,
        name="accounts-activate2"),
                       
    url(r'^register/$',
        accounts.registration,
        name="accounts-register"),

    url(r'^resetpassword/$',
        authviews.password_reset,
        {'template_name':'accounts/password_reset_form.html',
         'email_template_name':'accounts/password_reset_email.html'},
         name="accounts-password-reset"),

    url(r'^resetpassword/sent/$',
        authviews.password_reset_done,
        {'template_name':'accounts/password_reset_done.html'}),

    url(r'^resetpassword/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        authviews.password_reset_confirm,
        {'template_name':'accounts/password_reset_confirm.html'}),

    url(r'^resetpassword/complete/$',
        authviews.password_reset_complete,
        {'template_name':'accounts/password_reset_complete.html'}),

    url(r'^resetemail/$',
        accounts.email_reset,
        name="accounts-email-reset"),

    url(r'^resetemail/sent/$',
        accounts.email_reset_done),

    url(r'^resetemail/complete/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        accounts.email_reset_complete),
 
    url(r'^bulklicensechange/$',
        accounts.bulk_license_change,
        name="bulk-license-change"),

    url(r'^tosacceptance/$',
        accounts.tos_acceptance,
        name="tos-acceptance"),

    url(r'^$', accounts.home, name="accounts-home"),
    url(r'^edit/$', accounts.edit, name="accounts-edit"),
    url(r'^delete/$', accounts.delete, name="accounts-delete"),

    url(r'^pending/$', accounts.pending, name="accounts-pending"),

    url(r'^upload/file/$', accounts.upload_file, name="accounts-upload-file"),
    url(r'^upload/$', accounts.upload, name="accounts-upload"),
    url(r'^upload/html/$', accounts.upload, name="accounts-upload-html", kwargs=dict(no_flash=True)),    
    url(r'^describe/$', accounts.describe, name="accounts-describe"),
    url(r'^describe/license/$', accounts.describe_license, name="accounts-describe-license"),
    url(r'^describe/pack/', accounts.describe_pack, name="accounts-describe-pack"),
    url(r'^describe/sounds/', accounts.describe_sounds, name="accounts-describe-sounds"),
    url(r'^attribution/$', accounts.attribution, name="accounts-attribution"),
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
)
