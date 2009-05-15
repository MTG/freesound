# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
import django.contrib.auth.views as authviews
import messages.views as messages
import views as accounts
import django.contrib.auth.views as authviews

urlpatterns = patterns('accounts.views',
    url(r'^login/$', authviews.login, {'template_name': 'accounts/login.html'}, name="accounts-login"),
    url(r'^logout/$', authviews.logout, {'template_name': 'accounts/logout.html'}, name="accounts-logout"),
    url(r'^activate/(?P<activation_key>[^//]+)/$', accounts.activate_user, name="accounts-activate"),
    url(r'^register/$', accounts.registration, name="accounts-register"),
    url(r'^resetpassword/$', authviews.password_reset, {'template_name':'accounts/password_reset_form.html', 'email_template_name':'accounts/password_reset_email.html'}, name="accounts-password-reset"),
    url(r'^resetpassword/sent/$', authviews.password_reset_done, {'template_name':'accounts/password_reset_done.html'}),
    url(r'^resetpassword/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', authviews.password_reset_confirm, {'template_name':'accounts/password_reset_confirm.html'}),
    url(r'^resetpassword/complete/$', authviews.password_reset_complete, {'template_name':'accounts/password_reset_complete.html'}),
    
    url(r'^$', accounts.home, name="accounts-home"),
    url(r'^edit/$', accounts.edit, name="accounts-edit"),

    url(r'^upload/$', accounts.upload, name="accounts-upload"),
    url(r'^describe/$', accounts.describe, name="accounts-describe"),
    url(r'^attribution/$', accounts.attribution, name="accounts-attribution"),

    url(r'^messages/$', messages.inbox, name='messages'),
    url(r'^messages/sent/$', messages.sent_messages, name='messages-sent'),
    url(r'^messages/archived/$', messages.archived_messages, name='messages-archived'),
    url(r'^messages/changestate/$', messages.messages_change_state, name='messages-change-state'),
    url(r'^messages/(?P<message_id>\d+)/$', messages.message, name='message'),
    url(r'^messages/new/$', messages.new_message, name='messages-new'),
    url(r'^messages/new/(?P<username>[^//]+)/$', messages.new_message, name='messages-new'),
)