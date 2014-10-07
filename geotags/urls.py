# -*- coding: utf-8 -*-

#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from django.conf.urls import url, patterns
import geotags.views as geotags

urlpatterns = patterns('',
    url(r'^sounds_json/user/(?P<username>[^//]+)/$', geotags.geotags_for_user_json, name="geotags-for-user-json"),
    url(r'^sounds_json/user_latest/(?P<username>[^//]+)/$', geotags.geotags_for_user_latest_json, name="geotags-for-user-latest-json"),
    url(r'^sounds_json/pack/(?P<pack_id>\d+)/$', geotags.geotags_for_pack_json, name="geotags-for-pack-json"),
    url(r'^sounds_json/(?P<tag>[\w-]+)?/?$', geotags.geotags_json, name="geotags-json"),
    url(r'^geotags_box_json/$', geotags.geotags_box_json, name="geotags-box-json"),
    url(r'^infowindow/(?P<sound_id>\d+)/$', geotags.infowindow, name="geotags-infowindow"),
)