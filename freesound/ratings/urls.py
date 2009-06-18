# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

import views as ratings

urlpatterns = patterns('',
    url(r'^add/(?P<content_type_id>\d+)/(?P<object_id>\d+)/(?P<rating>\d)/$', ratings.rate, name="ratings-rate"),
)