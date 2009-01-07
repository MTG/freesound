# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns('forum.views',
    url(r'^$', 'forums', name='forums'),
    url(r'^(?P<forum_name_slug>[\w\-]+)/$', 'forum', name="forum"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/$', 'thread', name="thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$', 'post', name="post"),
    url(r'^add_post/$', 'add_post', name="post-add"),
    url(r'^edit_post/(?P<post_id>\d+)/$', 'edit_post', name="post-edit"),
)