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
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.conf import settings

from apiv2.models import ApiV2Client
from apiv2.apiv2_utils import ApiSearchPaginator
from forms import SoundCombinedSearchFormAPI
from utils.test_helpers import create_user_and_sounds

from exceptions import BadRequestException


class TestAPiViews(TestCase):
    fixtures = ['licenses']

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
                                            name='', url='', redirect_uri='https://freesound.org')
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
    fixtures = ['licenses']

    def test_cors_header(self):
        # Create App to login using token
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)

        c = ApiV2Client(user=user, status='OK', redirect_uri="https://freesound.com",
                        url="https://freesound.com", name="test")
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

    def test_encoding(self):
        # Create App to login using token
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)

        c = ApiV2Client(user=user, status='OK', redirect_uri="https://freesound.com",
                        url="https://freesound.com", name="test")
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


class ApiSearchPaginatorTest(TestCase):
    def test_page(self):
        paginator = ApiSearchPaginator([1, 2, 3, 4, 5], 5, 2)
        page = paginator.page(2)

        self.assertEquals(page, {'object_list': [1, 2, 3, 4, 5],
                                 'has_next': True,
                                 'has_previous': True,
                                 'has_other_pages': True,
                                 'next_page_number': 3,
                                 'previous_page_number': 1,
                                 'page_num': 2})


class TestSoundCombinedSearchFormAPI(SimpleTestCase):
    # Query
    def test_query_empty_valid(self):
        for query in [' ', '', '" "', '""', "' '", "''"]:
            form = SoundCombinedSearchFormAPI(data={'query': query})
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['query'], '')

    # Filter
    def test_filter_empty_invalid(self):
        for filt in ['', ' ']:
            form = SoundCombinedSearchFormAPI(data={'filter': filt})
            with self.assertRaisesMessage(BadRequestException, 'Invalid filter.'):
                self.assertFalse(form.is_valid())

    def test_filter_valid(self):
        filt = 'text'
        form = SoundCombinedSearchFormAPI(data={'filter': 'text'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['filter'], filt)

    # Descriptors
    def test_descriptors_empty_valid(self):
        form = SoundCombinedSearchFormAPI(data={})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['descriptors'], '')

    def test_descriptors_valid(self):
        descriptors = 'test'
        form = SoundCombinedSearchFormAPI(data={'descriptors': descriptors})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['descriptors'], descriptors)

    # Normalized
    def test_normalized_valid(self):
        normalized = '1'
        form = SoundCombinedSearchFormAPI(data={'normalized': normalized})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['normalized'], normalized)

    def test_normalized_bogus_valid(self):
        for normalized in ['0', '', 'test']:
            form = SoundCombinedSearchFormAPI(data={'normalized': normalized})
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['normalized'], '')

    # Page
    def test_page_empty_valid(self):
        form = SoundCombinedSearchFormAPI(data={})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['page'], 1)

    def test_page_bogus_valid(self):
        for page in ['', 'test']:
            form = SoundCombinedSearchFormAPI(data={'page': page})
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['page'], 1)

    # Sort
    def test_sort_empty_valid(self):
        form = SoundCombinedSearchFormAPI(data={})
        self.assertTrue(form.is_valid())
        sort = form.cleaned_data['sort']
        self.assertEqual(len(sort), 1)
        self.assertEqual(sort[0], 'score desc')

    def test_sort_multiple_valid(self):
        form = SoundCombinedSearchFormAPI(data={'sort': 'rating_desc'})
        self.assertTrue(form.is_valid())
        sort = form.cleaned_data['sort']
        self.assertEqual(sort[0], "avg_rating desc")
        self.assertEqual(len(sort), 2)
        self.assertEqual(sort[1], "num_ratings desc")

    # Normalized
    def test_group_by_pack_valid(self):
        group_by_pack = '1'
        form = SoundCombinedSearchFormAPI(data={'group_by_pack': group_by_pack})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['group_by_pack'], group_by_pack)

    def test_group_by_pack_bogus_valid(self):
        for group_by_pack in ['0', '', 'test']:
            form = SoundCombinedSearchFormAPI(data={'group_by_pack': group_by_pack})
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data['group_by_pack'], '')

    # Page size
    def test_page_size_empty_valid(self):
        form = SoundCombinedSearchFormAPI(data={})
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data[settings.APIV2['PAGE_SIZE_QUERY_PARAM']], settings.APIV2['PAGE_SIZE'])

    def test_page_size_max_valid(self):
        param = settings.APIV2['PAGE_SIZE_QUERY_PARAM']
        form = SoundCombinedSearchFormAPI(data={param: settings.APIV2['MAX_PAGE_SIZE'] + 1})
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data[param], settings.APIV2['MAX_PAGE_SIZE'])

    # Descriptors filter
    def test_descriptors_filter_empty_invalid(self):
        for descriptors_filter in ['', ' ']:
            form = SoundCombinedSearchFormAPI(data={'descriptors_filter': descriptors_filter})
            with self.assertRaisesMessage(BadRequestException, 'Invalid descriptors_filter.'):
                self.assertFalse(form.is_valid())

    def test_descriptors_filter_valid(self):
        descriptors_filter = 'test'
        form = SoundCombinedSearchFormAPI(data={'descriptors_filter': descriptors_filter})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['descriptors_filter'], descriptors_filter)

    # Target
    def test_target_empty_invalid(self):
        for target in ['', ' ']:
            form = SoundCombinedSearchFormAPI(data={'target': target})
            with self.assertRaisesMessage(BadRequestException, 'Invalid target.'):
                self.assertFalse(form.is_valid())

    def test_target_valid(self):
        target = 'test'
        form = SoundCombinedSearchFormAPI(data={'target': target})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['target'], target)


class TestSoundListSerializer(TestCase):

    def test_num_fields(self):
        # TODO: Test that serializer returns only fields included in fields parameter of the request
        pass

    def test_field_contents(self):
        # TODO: Test that the content of the fields returned by the serializer is correct
        pass

    def test_num_queries(self):
        # TODO: Test that the number of queries performed to the DB when serializing sounds does not change
        # TODO: depending on the fields we include. Test with the serialization of only 1 sound and also with
        # TODO: the serialization of N sounds
        pass
