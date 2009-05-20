# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
import views

urlpatterns = patterns('forum.views',
    url(r'^$', views.forums, name='forums-forums'),
    url(r'^(?P<forum_name_slug>[\w\-]+)/$', views.forum, name="forums-forum"),
    url(r'^(?P<forum_name_slug>[\w\-]+)/new-thread/$', views.new_thread, name="forums-new-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/$', views.thread, name="forums-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/unsubscribe/$', views.unsubscribe_from_thread, name="forums-thread-unsubscribe"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$', views.post, name="forums-post"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/reply/$', views.reply, name="forums-reply"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/reply/$', views.reply, name="forums-reply-quote"),
)