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

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from geotags.models import GeoTag
from sounds.models import Sound


class GeoTagsTests(TestCase):

    fixtures = ['licenses', 'sounds']

    def check_context(self, context, values):
        for k, v in values.items():
            self.assertIn(k, context)
            self.assertEqual(context[k], v)

    def test_browse_geotags(self):
        resp = self.client.get(reverse('geotags', kwargs={'tag': 'soundscape'}))
        check_values = {'tag': 'soundscape', 'username': None}
        self.check_context(resp.context, check_values)

    def test_geotags_embed(self):
        resp = self.client.get(reverse('embed-geotags'))
        check_values = {'m_width': 942, 'm_height': 600, 'cluster': True, 'center_lat': None, 'center_lon': None,
                        'zoom': None, 'username': None}
        self.check_context(resp.context, check_values)

    def test_browse_geotags_for_user(self):
        user = User.objects.get(username='Anton')
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': 'Anton'}))
        check_values = {'tag': None, 'username': user.username}
        self.check_context(resp.context, check_values)

    def test_browse_geotags_for_user_oldusername(self):
        user = User.objects.get(username='Anton')
        user.username = "new_username"
        user.save()
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': 'Anton'}))
        self.assertRedirects(resp, reverse('geotags-for-user', kwargs={'username': user.username}), status_code=301)

    def test_browse_geotags_for_user_deleted_user(self):
        user = User.objects.get(username='Anton')
        user.profile.delete_user()
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': 'Anton'}))
        self.assertEqual(resp.status_code, 404)

    def test_geotags_infowindow(self):
        sound = Sound.objects.first()
        gt = GeoTag.objects.create(sound=sound, lat=45.8498, lon=-62.6879, zoom=9)
        resp = self.client.get(reverse('geotags-infowindow', kwargs={'sound_id': sound.id}))
        self.check_context(resp.context, {'sound': sound})
        self.assertContains(resp, f'href="/people/{sound.user.username}/sounds/{sound.id}/"')

    def test_browse_geotags_case_insensitive(self):
        user = User.objects.get(username='Anton')
        sounds = list(Sound.objects.filter(user=user)[:2])

        tag = 'uniqueTag'
        sounds[1].set_tags([tag])
        sounds[0].set_tags([tag.upper()])

        lat = 45.8498
        lon = -62.6879
        
        for sound in sounds:
            GeoTag.objects.create(sound=sound, lat=lat + 0.0001, lon=lon + 0.0001, zoom=9)

        resp = self.client.get(reverse('geotags-barray', kwargs={'tag': tag}))
        # Response contains 3 int32 objects per sound: id, lat and lng. Total size = 3 * 4 bytes = 12 bytes
        n_sounds = len(resp.content) // 12
        self.assertEqual(n_sounds, 2)

    def test_browse_geotags_for_query(self):
        resp = self.client.get(reverse('geotags-query') + f'?q=barcelona')
        check_values = {'query_description': '"barcelona"'}
        self.check_context(resp.context, check_values)
