# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
import ratings.views as ratings

urlpatterns = patterns('',
    url(r'^add/(?P<content_type_id>\d+)/(?P<object_id>\d+)/(?P<rating>\d)/$', ratings.add, name="ratings-add"),
)