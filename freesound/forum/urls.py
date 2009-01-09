# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns('forum.views',
    url(r'^$', 'forums', name='forums-forums'),
    url(r'^(?P<forum_name_slug>[\w\-]+)/$', 'forum', name="forums-forum"),
    url(r'^(?P<forum_name_slug>[\w\-]+)/new-thread/$', 'new_thread', name="forums-new-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/$', 'thread', name="forums-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$', 'post', name="forums-post"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/reply/$', 'reply', name="forums-reply"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/reply/$', 'reply', name="forums-reply-quote"),
)