# -*- coding: utf-8 -*-

from django.conf.urls.defaults import url, patterns
import geotags.views as geotags

urlpatterns = patterns('',
    url(r'^sounds_json/user/(?P<username>[^//]+)/$', geotags.geotags_for_user_json, name="geotags-for-user-json"),
    url(r'^sounds_json/user_latest/(?P<username>[^//]+)/$', geotags.geotags_for_user_latest_json, name="geotags-for-user-latest-json"),
    url(r'^sounds_json/pack/(?P<pack_id>\d+)/$', geotags.geotags_for_pack_json, name="geotags-for-pack-json"),
    url(r'^sounds_json/(?P<tag>[\w-]+)?/?$', geotags.geotags_json, name="geotags-json"),
    url(r'^infowindow/(?P<sound_id>\d+)/$', geotags.infowindow, name="geotags-infowindow"),
)