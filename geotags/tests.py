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

    fixtures = ['sounds']

    def check_context(self, context, values):
        for k, v in values.items():
            self.assertIn(k, context)
            self.assertEquals(context[k], v)

    def test_browse_geotags(self):
        resp = self.client.get(reverse('geotags', kwargs={'tag': 'soundscape'}))
        check_values = {'tag': 'soundscape', 'for_user': None}
        self.check_context(resp.context, check_values)

    def test_browse_geotags_box(self):
        resp = self.client.get(reverse('geotags-box'))
        check_values = {'m_width': 900, 'm_height': 600, 'clusters': 'on', 'center_lat': None, 'center_lon': None,
                        'zoom': None, 'username': None}
        self.check_context(resp.context, check_values)

    def test_geotags_box_iframe(self):
        resp = self.client.get(reverse('embed-geotags-box-iframe'))
        check_values = {'m_width': 900, 'm_height': 600, 'clusters': 'on', 'center_lat': None, 'center_lon': None,
                        'zoom': None, 'username': None}
        self.check_context(resp.context, check_values)

    def test_browse_geotags_for_user(self):
        user = User.objects.get(username='Anton')
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': 'Anton'}))
        check_values = {'tag': None, 'for_user': user}
        self.check_context(resp.context, check_values)

    def test_browse_geotags_for_user_oldusername(self):
        user = User.objects.get(username='Anton')
        user.username = "new_username"
        user.save()
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': 'Anton'}))
        check_values = {'tag': None, 'for_user': user}
        self.check_context(resp.context, check_values)

    def test_geotags_infowindow(self):
        sound = Sound.objects.first()
        gt = GeoTag.objects.create(user=sound.user, lat=45.8498, lon=-62.6879, zoom=9)
        sound.geotag = gt
        sound.save()
        resp = self.client.get(reverse('geotags-infowindow', kwargs={'sound_id': sound.id}))
        self.check_context(resp.context, {'sound': sound})
        self.assertInHTML('<a class="title" target="_blank" href="/people/Anton/sounds/16/">Glass A mf.wav</a>', resp.content)
