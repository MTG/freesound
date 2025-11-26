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

from django.test import Client, TestCase
from django.urls import reverse

from sounds.models import Pack, Sound


class OldSoundLinksRedirectTestCase(TestCase):
    fixtures = ["licenses", "sounds"]

    def setUp(self):
        self.sound = Sound.objects.all()[0]

    def test_old_sound_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        response = self.client.get(reverse("old-sound-page"), data={"id": self.sound.id})
        self.assertEqual(response.status_code, 301)

        # id is valid but has a space after it
        response = self.client.get(reverse("old-sound-page"), data={"id": "%d " % self.sound.id})
        self.assertEqual(response.status_code, 301)

    def test_old_sound_link_redirect_not_exists_id(self):
        # 404 id does not exist
        response = self.client.get(reverse("old-sound-page"), data={"id": 0}, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_old_sound_link_redirect_invalid_id(self):
        # 404 invalid id
        response = self.client.get(reverse("old-sound-page"), data={"id": "invalid_id"}, follow=True)
        self.assertEqual(response.status_code, 404)


class OldPackLinksRedirectTestCase(TestCase):
    fixtures = ["packs"]

    def setUp(self):
        self.client = Client()
        self.pack = Pack.objects.all()[0]

    def test_old_pack_link_redirect_ok(self):
        response = self.client.get(reverse("old-pack-page"), data={"id": self.pack.id})
        self.assertEqual(response.status_code, 301)

        # id is valid but has a space after it
        response = self.client.get(reverse("old-pack-page"), data={"id": "%d " % self.pack.id})
        self.assertEqual(response.status_code, 301)

    def test_old_pack_link_redirect_not_exists_id(self):
        response = self.client.get(reverse("old-pack-page"), data={"id": 0}, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_old_pack_link_redirect_invalid_id(self):
        response = self.client.get(reverse("old-pack-page"), data={"id": "invalid_id"}, follow=True)
        self.assertEqual(response.status_code, 404)
