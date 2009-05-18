# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

import views as geotags

urlpatterns = patterns('',
    url(r'^infowindow/(?P<sound_id>\d+)/$', geotags.infowindow, name="geotags-infowindow"),
)