# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

import views as geotags

urlpatterns = patterns('',
    url(r'^sounds_json/(?P<tag>[\w-]+)?/?$', geotags.getags_json, name="geotags-json"),
    url(r'^infowindow/(?P<sound_id>\d+)/$', geotags.infowindow, name="geotags-infowindow"),
)