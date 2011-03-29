# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
import comments.views as comments

urlpatterns = patterns('',
    url(r'^delete/(?P<comment_id>\d+)/$', comments.delete, name="comment-delete"),
)