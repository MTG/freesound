# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
import forum.views as forum

urlpatterns = patterns('forum.views',
    url(r'^$', forum.forums, name='forums-forums'),
    url(r'^(?P<forum_name_slug>[\w\-]+)/$', forum.forum, name="forums-forum"),
    url(r'^(?P<forum_name_slug>[\w\-]+)/new-thread/$', forum.new_thread, name="forums-new-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/$', forum.thread, name="forums-thread"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/unsubscribe/$', forum.unsubscribe_from_thread, name="forums-thread-unsubscribe"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$', forum.post, name="forums-post"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/reply/$', forum.reply, name="forums-reply"),
    url(r'^(?P<forum_name_slug>[\w-]+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/reply/$', forum.reply, name="forums-reply-quote"),

    url(r'^post/(?P<post_id>\d+)/edit/$', forum.post_edit, name="forums-post-edit"),
    url(r'^post/(?P<post_id>\d+)/delete/$', forum.post_delete, name="forums-post-delete"),
    url(r'^post/(?P<post_id>\d+)/delete-confirm/$', forum.post_delete_confirm, name="forums-post-delete-confirm"),
)
