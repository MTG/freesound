# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
import django.contrib.auth.views as authviews
import messages.views as messages

urlpatterns = patterns('accounts.views',
    url(r'^login/$', authviews.login, {'template_name': 'accounts/login.html'}, name="accounts-login"),
    url(r'^logout/$', authviews.logout, {'template_name': 'accounts/logout.html'}, name="accounts-logout"),
    url(r'^$', 'home', name="accounts-home"),
    url(r'^edit/$', 'edit', name="accounts-edit"),

    url(r'^upload/$', 'upload', name="accounts-upload"),
    url(r'^upload/(?P<unique_id>\d{10})/$', 'upload', name="accounts-upload-unique"),
    url(r'^upload/progress/(?P<unique_id>\d{10})/$', 'upload_progress', name="accounts-upload-progress"),
    url(r'^describe/$', 'describe', name="accounts-describe"),
    url(r'^attribution/$', 'attribution', name="accounts-attribution"),

    url(r'^messages/$', messages.messages, name='messages'),
    url(r'^messages/(?P<message_id>\d+)/$', messages.message, name='message'),
    url(r'^messages/sent/$', messages.sent, name='messages-sent'),
)