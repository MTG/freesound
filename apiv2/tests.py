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

from django.test import TestCase
from django.core.urlresolvers import reverse
from sounds.tests import create_user_and_sounds


class TestAPiViews(TestCase):

    fixtures = ['initial_data']

    def test_pack_views_response_ok(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)
        for sound in sounds:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")

        # Login so api returns session login based responses
        self.client.login(username=user.username, password='testpass')

        # 200 response on pack instance
        resp = self.client.get(reverse('apiv2-pack-instance', kwargs={'pk': packs[0].id}))
        self.assertEqual(resp.status_code, 200)

        # 200 response on pack instance sounds list
        resp = self.client.get(reverse('apiv2-pack-sound-list', kwargs={'pk': packs[0].id}))
        self.assertEqual(resp.status_code, 200)

        # 200 response on pack instance download
        # This test does not work because it needs https connection.
        # TODO: see how to etst that (will be needed for many other api tests)
        # resp = self.client.get(reverse('apiv2-pack-download', kwargs={'pk': packs[0].id}))
        # self.assertEqual(resp.status_code, 200)
