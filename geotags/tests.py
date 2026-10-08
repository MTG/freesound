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

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from pytest_django.asserts import assertContains, assertRedirects

from geotags.models import GeoTag
from sounds.models import Sound


@pytest.fixture
def geotag_data(load_fixtures):
    load_fixtures(["licenses", "sounds"])


class TestGeoTags:
    @staticmethod
    def check_context(context, values):
        for k, v in values.items():
            assert k in context
            assert context[k] == v

    def test_browse_geotags(self, geotag_data, client):
        resp = client.get(reverse("geotags", kwargs={"tag": "soundscape"}))
        check_values = {"tag": "soundscape", "username": None}
        self.check_context(resp.context, check_values)

    def test_geotags_embed(self, geotag_data, client):
        resp = client.get(reverse("embed-geotags"))
        check_values = {
            "m_width": 942,
            "m_height": 600,
            "cluster": True,
            "center_lat": None,
            "center_lon": None,
            "zoom": None,
            "username": None,
        }
        self.check_context(resp.context, check_values)

    def test_browse_geotags_for_user(self, geotag_data, client):
        user = User.objects.get(username="Anton")
        resp = client.get(reverse("geotags-for-user", kwargs={"username": "Anton"}))
        check_values = {"tag": None, "username": user.username}
        self.check_context(resp.context, check_values)

    def test_browse_geotags_for_user_oldusername(self, geotag_data, client):
        user = User.objects.get(username="Anton")
        user.username = "new_username"
        user.save()
        resp = client.get(reverse("geotags-for-user", kwargs={"username": "Anton"}))
        assertRedirects(resp, reverse("geotags-for-user", kwargs={"username": user.username}), status_code=301)

    def test_browse_geotags_for_user_deleted_user(self, geotag_data, client):
        user = User.objects.get(username="Anton")
        user.profile.delete_user()
        resp = client.get(reverse("geotags-for-user", kwargs={"username": "Anton"}))
        assert resp.status_code == 404

    def test_browse_geotags_for_sound_without_geotag_returns_404(self, geotag_data, client):
        sound = Sound.objects.first()
        # Ensure sound has no geotag associated
        GeoTag.objects.filter(sound=sound).delete()

        url = reverse("sound-geotag", kwargs={"username": sound.user.username, "sound_id": sound.id})
        resp = client.get(url)
        assert resp.status_code == 404

    def test_geotags_infowindow(self, geotag_data, client):
        sound = Sound.objects.first()
        gt = GeoTag.objects.create(sound=sound, lat=45.8498, lon=-62.6879, zoom=9)
        resp = client.get(reverse("geotags-infowindow", kwargs={"sound_id": sound.id}))
        self.check_context(resp.context, {"sound": sound})
        assertContains(resp, f'href="/people/{sound.user.username}/sounds/{sound.id}/"')

    def test_browse_geotags_case_insensitive(self, geotag_data, client):
        user = User.objects.get(username="Anton")
        sounds = list(Sound.objects.filter(user=user)[:2])

        tag = "uniqueTag"
        sounds[1].set_tags([tag])
        sounds[0].set_tags([tag.upper()])

        lat = 45.8498
        lon = -62.6879

        for sound in sounds:
            GeoTag.objects.create(sound=sound, lat=lat + 0.0001, lon=lon + 0.0001, zoom=9)

        resp = client.get(reverse("geotags-barray", kwargs={"tag": tag}))
        # Response contains 3 int32 objects per sound: id, lat and lng. Total size = 3 * 4 bytes = 12 bytes
        n_sounds = len(resp.content) // 12
        assert n_sounds == 2

    def test_browse_geotags_for_query(self, geotag_data, client):
        resp = client.get(reverse("geotags-query") + "?q=barcelona")
        check_values = {"query_description": '"barcelona"'}
        self.check_context(resp.context, check_values)

    def test_geotags_for_query_barray_invalid_filter_returns_empty(self, geotag_data, client):
        # A corrupted/invalid filter sets sqp.errors, which must short-circuit before
        # Solr; the endpoint returns an empty bytearray rather than crashing.
        resp = client.get(reverse("geotags-for-query-barray") + "?f=samplerate%3Aabc")
        assert resp.status_code == 200
        assert len(resp.content) == 0
