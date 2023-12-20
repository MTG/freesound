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

from django.urls import path, re_path
import geotags.views as geotags

urlpatterns = [
    path('sounds_barray/user/<username>/', geotags.geotags_for_user_barray, name="geotags-for-user-barray"),
    path(
        'sounds_barray/user_latest/<username>/',
        geotags.geotags_for_user_latest_barray,
        name="geotags-for-user-latest-barray"
    ),
    path('sounds_barray/pack/<int:pack_id>/', geotags.geotags_for_pack_barray, name="geotags-for-pack-barray"),
    path('sounds_barray/sound/<int:sound_id>/', geotags.geotag_for_sound_barray, name="geotags-for-sound-barray"),
    re_path(r'^sounds_barray/(?P<tag>[\w-]+)?/?$', geotags.geotags_barray, name="geotags-barray"),
    path('geotags_box_barray/', geotags.geotags_box_barray, name="geotags-box-barray"),
    path('infowindow/<int:sound_id>/', geotags.infowindow, name="geotags-infowindow"),
]
