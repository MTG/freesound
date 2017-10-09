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
import base64
from django.test import TestCase
from django.urls import reverse
from sounds.tests import create_user_and_sounds
from models import ApiV2Client

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
        # This test uses a https connection.
        resp = self.client.get(reverse('apiv2-pack-download',
            kwargs={'pk': packs[0].id}), secure=True)
        self.assertEqual(resp.status_code, 200)

    def test_oauth2_response_ok(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)
        client = ApiV2Client.objects.create(user=user, description='',
                name='', url='', redirect_uri='http://freesound.org')
        # Login so api returns session login based responses
        self.client.login(username=user.username, password='testpass')

        # 200 response on Oauth2 authorize
        resp = self.client.post(reverse('oauth2_provider:authorize'),
                {'client_id': client.id, 'response_type': 'code'}, secure=True)
        self.assertEqual(resp.status_code, 200)

        # 302 response on Oauth2 logout and authorize
        resp = self.client.post(reverse('oauth2_provider:logout_and_authorize'),
                {'client_id': client.id}, secure=True)
        self.assertEqual(resp.status_code, 302)

    def test_basic_user_response_ok(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)
        # 200 response on register page
        resp = self.client.get(reverse('apiv2-registration'), secure=True)
        self.assertEqual(resp.status_code, 200)

        # 200 response on login page
        resp = self.client.get(reverse('api-login'), secure=True)
        self.assertEqual(resp.status_code, 200)

        self.client.login(username=user.username, password='testpass')

        # 200 response on keys page
        resp = self.client.get(reverse('apiv2-apply'), secure=True)
        self.assertEqual(resp.status_code, 200)

        # 302 response on logout page
        resp = self.client.get(reverse('api-logout'), secure=True)
        self.assertEqual(resp.status_code, 302)


class TestAPI(TestCase):

    fixtures = ['initial_data']

    def test_cors_header(self):
        # Create App to login using token
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)

        c = ApiV2Client(user=user, status='OK', redirect_uri="http://www.freesound.com",
                url="http://freesound.com", name="test")
        c.save()

        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")

        headers = {
            'HTTP_AUTHORIZATION': 'Token %s' % c.key,
            'HTTP_ORIGIN': 'https://www.google.com'
        }
        resp = self.client.options(reverse('apiv2-sound-instance',
            kwargs={'pk': sound.id}), secure=True, **headers)
        self.assertEqual(resp.status_code, 200)
        # Check if header is present
        self.assertEqual(resp['ACCESS-CONTROL-ALLOW-ORIGIN'], '*')

    def test_encodig(self):
        # Create App to login using token
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)

        c = ApiV2Client(user=user, status='OK', redirect_uri="http://www.freesound.com",
                url="http://freesound.com", name="test")
        c.save()

        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")

        headers = {
            'HTTP_AUTHORIZATION': 'Token %s' % c.key,
        }
        # make query that can't be decoded
        resp = self.client.options("/apiv2/search/text/?query=ambient&filter=tag:(rain%20OR%CAfe)", secure=True, **headers)
        self.assertEqual(resp.status_code, 200)
