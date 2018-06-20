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

from django.conf.urls import url
import geotags.views as geotags

urlpatterns = [
    url(r'^sounds_barray/user/(?P<username>[^//]+)/$', geotags.geotags_for_user_barray, name="geotags-for-user-barray"),
    url(r'^sounds_barray/user_latest/(?P<username>[^//]+)/$', geotags.geotags_for_user_latest_barray, name="geotags-for-user-latest-barray"),
    url(r'^sounds_barray/pack/(?P<pack_id>\d+)/$', geotags.geotags_for_pack_barray, name="geotags-for-pack-barray"),
    url(r'^sounds_barray/sound/(?P<sound_id>\d+)/$', geotags.geotag_for_sound_barray, name="geotags-for-sound-barray"),
    url(r'^sounds_barray/(?P<tag>[\w-]+)?/?$', geotags.geotags_barray, name="geotags-barray"),
    url(r'^geotags_box_barray/$', geotags.geotags_box_barray, name="geotags-box-barray"),
    url(r'^infowindow/(?P<sound_id>\d+)/$', geotags.infowindow, name="geotags-infowindow"),
]
