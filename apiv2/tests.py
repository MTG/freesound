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
from django.test import TestCase, SimpleTestCase, RequestFactory
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site

from apiv2.models import ApiV2Client
from apiv2.apiv2_utils import ApiSearchPaginator
from apiv2.serializers import SoundListSerializer, DEFAULT_FIELDS_IN_SOUND_LIST, SoundSerializer
from bookmarks.models import BookmarkCategory, Bookmark
from .forms import SoundCombinedSearchFormAPI
from sounds.models import Sound
from utils.test_helpers import create_user_and_sounds

from .exceptions import BadRequestException


class TestAPiViews(TestCase):
    fixtures = ['licenses']

    def test_pack_views_response_ok(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)
        for sound in sounds:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")

        # Login so api returns session login based responses
        self.client.force_login(user)

        # 200 response on pack instance
        resp = self.client.get(reverse('apiv2-pack-instance', kwargs={'pk': packs[0].id}))
        self.assertEqual(resp.status_code, 200)

        # 200 response on pack instance sounds list (make it return all fields)
        resp = self.client.get(reverse('apiv2-pack-sound-list', kwargs={'pk': packs[0].id})  + '?fields=*')
        self.assertEqual(resp.status_code, 200)

        # 200 response on pack instance download
        # This test uses a https connection.
        resp = self.client.get(reverse('apiv2-pack-download',
                               kwargs={'pk': packs[0].id}), secure=True)
        self.assertEqual(resp.status_code, 200)


    def test_basic_user_response_ok(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)

        # 200 response on login page
        resp = self.client.get(reverse('api-login'), secure=True)
        self.assertEqual(resp.status_code, 200)

        self.client.force_login(user)

        # 200 response on keys page
        resp = self.client.get(reverse('apiv2-apply'), secure=True)
        self.assertEqual(resp.status_code, 200)

        # 302 response on logout page
        resp = self.client.get(reverse('api-logout'), secure=True)
        self.assertEqual(resp.status_code, 302)


    def test_user_views_response_ok(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)
        for sound in sounds:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")
        self.client.force_login(user)

        # 200 response on user instance
        resp = self.client.get(reverse('apiv2-user-instance', kwargs={'username': user.username}))
        self.assertEqual(resp.status_code, 200)

        # 200 response on user instance sounds list (add all fields to return list)
        resp = self.client.get(reverse('apiv2-user-sound-list', kwargs={'username': user.username}) + '?fields=*')
        self.assertEqual(resp.status_code, 200)


    def test_sound_views_response_ok(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)
        for sound in sounds:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")
        self.client.force_login(user)

        # 200 response on user instance
        resp = self.client.get(reverse('apiv2-sound-instance', kwargs={'pk': sounds[0].id}))
        self.assertEqual(resp.status_code, 200)



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
            'HTTP_AUTHORIZATION': f'Token {c.key}',
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
            'HTTP_AUTHORIZATION': f'Token {c.key}',
        }
        # make query that can't be decoded
        resp = self.client.options("/apiv2/search/text/?query=ambient&filter=tag:(rain%20OR%CAfe)", secure=True, **headers)
        self.assertEqual(resp.status_code, 200)


class ApiSearchPaginatorTest(TestCase):
    def test_page(self):
        paginator = ApiSearchPaginator([1, 2, 3, 4, 5], 5, 2)
        page = paginator.page(2)

        self.assertEqual(page, {'object_list': [1, 2, 3, 4, 5],
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

    fixtures = ['licenses', 'sounds']

    def setUp(self):
        self.ss = Sound.objects.all()[0:5]
        self.sids = [s.id for s in self.ss]
        self.factory = RequestFactory()

    def test_num_fields(self):
        # Test that serializer returns only fields included in fields parameter of the request

        sounds_dict = Sound.objects.dict_ids(sound_ids=self.sids)

        # When 'fields' parameter is not used, return default ones
        dummy_request = self.factory.get(reverse('apiv2-sound-search'), {'fields': ''})
        serialized_sound = SoundListSerializer(list(sounds_dict.values())[0], context={'request': dummy_request}).data
        self.assertCountEqual(list(serialized_sound.keys()), DEFAULT_FIELDS_IN_SOUND_LIST.split(','))

        # When only some parameters are specified
        fields_parameter = 'id,username'
        dummy_request = self.factory.get(reverse('apiv2-sound-search'), {'fields': fields_parameter})
        serialized_sound = SoundListSerializer(list(sounds_dict.values())[0], context={'request': dummy_request}).data
        self.assertCountEqual(list(serialized_sound.keys()), fields_parameter.split(','))

        # When all parameters are specified
        fields_parameter = ','.join(SoundListSerializer.Meta.fields)
        dummy_request = self.factory.get(reverse('apiv2-sound-search'), {'fields': fields_parameter})
        serialized_sound = SoundListSerializer(list(sounds_dict.values())[0], context={'request': dummy_request}).data
        self.assertCountEqual(list(serialized_sound.keys()), fields_parameter.split(','))

    def test_num_queries(self):
        # Test that the serializer does not perform any extra query when serializing sounds regardless of the number
        # of sounds and the number of requested fields. This will be as long as sound object passed to the serializer
        # has been obtained using Sound.objects.dict_ids or Sound.objects.bulk_query_id

        # Make sure sound content type and site objects are cached to avoid further queries
        ContentType.objects.get_for_model(Sound)
        Site.objects.get_current()

        field_sets = [
            '',  # default fields
            ','.join(SoundListSerializer.Meta.fields),  # all fields
        ]

        # Test when serializing a single sound
        for field_set in field_sets:
            sounds_dict = Sound.objects.dict_ids(sound_ids=self.sids[0], 
                include_audio_descriptors=True,
                include_similarity_vectors=True,
                include_remix_subqueries=True)
            with self.assertNumQueries(0):
                dummy_request = self.factory.get(reverse('apiv2-sound-search'), {'fields': field_set})
                # Call serializer .data to actually get the data and potentially trigger unwanted extra queries
                _ = SoundListSerializer(list(sounds_dict.values())[0], context={'request': dummy_request}).data

        # Test when serializing multiple sounds
        for field_set in field_sets:
            sounds_dict = Sound.objects.dict_ids(sound_ids=self.sids, 
                include_audio_descriptors=True,
                include_similarity_vectors=True,
                include_remix_subqueries=True)
            with self.assertNumQueries(0):
                dummy_request = self.factory.get(reverse('apiv2-sound-search'), {'fields': field_set})
                for sound in sounds_dict.values():
                    # Call serializer .data to actually get the data and potentially trigger unwanted extra queries
                    _ = SoundListSerializer(sound, context={'request': dummy_request}).data


class TestSoundSerializer(TestCase):

    fixtures = ['licenses', 'sounds']

    def setUp(self):
        self.sound_id = Sound.objects.first().id
        self.factory = RequestFactory()

    def test_num_fields_and_num_queries(self):
        
        # Make sure sound content type and site objects are cached to avoid further queries
        ContentType.objects.get_for_model(Sound)
        Site.objects.get_current()

        with self.assertNumQueries(1):
            # Test that the serialized sound instance includes all fields in the serializer and does not perform any
            # extra query. Because in this test we get sound info using Sound.objects.bulk_query_id, the serializer
            # should perform no extra queries to render the data
            sound = Sound.objects.bulk_query_id(self.sound_id, 
                                                include_audio_descriptors=True, 
                                                include_similarity_vectors=True, 
                                                include_remix_subqueries=True)[0]
            dummy_request = self.factory.get(reverse('apiv2-sound-instance', args=[self.sound_id]) + '?fields=*')
            SoundSerializer(sound, context={'request': dummy_request}).data
            
class TestApiV2Client(TestCase):

    def test_urls_length_validation(self):
        """URLs are limited to a length of 200 characters at the DB level, test that passing a longer URL raised a
        for validation error instead of a DB error.
        """
        user = User.objects.create_user("testuser")
        self.client.force_login(user)
        resp = self.client.post(reverse('apiv2-apply'), data={
            'name': 'Name for the app',
            'url': 'http://example.com/a/super/long/paaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                   'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                   'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaath',
            'redirect_uri': 'http://example.com/a/super/long/paaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaath',
            'description': 'test description',
            'accepted_tos': '1',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('redirect_uri', resp.context['form'].errors)
        self.assertIn('url', resp.context['form'].errors)


class TestMeResources(TestCase):

    fixtures = ['licenses']

    def setUp(self):
        # Create users
        self.end_user_password = 'endpass'
        self.end_user = User.objects.create_user("end_user", password=self.end_user_password, email='enduser@mail.com')
        self.dev_user = User.objects.create_user("dev_user", password='devpass', email='devuser@mail.com')

        # Create clients
        client = ApiV2Client.objects.create(
            name='PasswordClient',
            user=self.dev_user,
            allow_oauth_password_grant=True,
        )

        # Get access token for end_user
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                'grant_type': 'password',
                'username': self.end_user.username,
                'password': self.end_user_password,
            }, secure=True)
        self.auth_headers = {
            'HTTP_AUTHORIZATION': f'Bearer {resp.json()["access_token"]}',
        }
        
        # Create sounds and content
        _, _, sounds = create_user_and_sounds(user=self.end_user, num_sounds=5, num_packs=1)
        for sound in sounds:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")

        self.category = BookmarkCategory.objects.create(name='Category1', user=self.end_user)
        Bookmark.objects.create(user=self.end_user, sound_id=sounds[0].id)
        Bookmark.objects.create(user=self.end_user, sound_id=sounds[1].id)
        Bookmark.objects.create(user=self.end_user, sound_id=sounds[2].id, category=self.category)
        Bookmark.objects.create(user=self.end_user, sound_id=sounds[3].id, category=self.category)

    def test_me_resource(self):
        # 200 response on me resource
        resp = self.client.get(reverse('apiv2-me'), secure=True, **self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['username'], self.end_user.username)
    
    def test_bookmark_resources(self):
        # 200 response on list of bookmark categories
        resp = self.client.get(reverse('apiv2-me-bookmark-categories'), secure=True, **self.auth_headers)
        self.assertEqual(resp.status_code, 200)

        # 200 response on getting sounds for bookmark category without name
        resp = self.client.get(reverse('apiv2-me-bookmark-category-sounds', kwargs={'category_id': 0}) + '?fields=*', secure=True, **self.auth_headers)
        self.assertEqual(resp.status_code, 200)

        # 200 response on getting sounds for bookmark category without name
        resp = self.client.get(reverse('apiv2-me-bookmark-category-sounds', kwargs={'category_id': self.category.id}) + '?fields=*', secure=True, **self.auth_headers)
        self.assertEqual(resp.status_code, 200)


class APIAuthenticationTestCase(TestCase):

    def setUp(self):
        # Create users
        self.end_user_password = 'endpass'
        self.end_user = User.objects.create_user("end_user", password=self.end_user_password, email='enduser@mail.com')
        self.dev_user = User.objects.create_user("dev_user", password='devpass', email='devuser@mail.com')

        # Create clients
        ApiV2Client.objects.create(
            name='PasswordClient',
            user=self.dev_user,
            allow_oauth_password_grant=True,
        )
        ApiV2Client.objects.create(
            name='AuthorizationCodeClient',
            user=self.dev_user,
            allow_oauth_password_grant=False,
        )

    @staticmethod
    def get_params_from_url(url):
        params_part = url.split('?')[1]
        return {item.split('=')[0]: item.split('=')[1] for item in params_part.split('&')}

    @staticmethod
    def fragment_params_from_url(url):
        params_part = url.split('#')[1]
        return {item.split('=')[0]: item.split('=')[1] for item in params_part.split('&')}

    def check_dict_has_fields(self, dictionary, fields):
        for field in fields:
            self.assertIn(field, dictionary)

    def check_access_token_response_fields(self, resp):
        self.check_dict_has_fields(
            resp.json(), ['expires_in', 'scope', 'refresh_token', 'access_token', 'token_type'])

    def check_redirect_uri_access_token_frag_params(self, params):
        self.check_dict_has_fields(
            params, ['expires_in', 'scope', 'access_token', 'token_type'])

    def test_oauth2_password_grant_flow(self):

        # Return 'unauthorized_client' when trying password grant with a client with 'allow_oauth_password_grant' set
        # to false
        client = ApiV2Client.objects.get(name='AuthorizationCodeClient')
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                'grant_type': 'password',
                'username': self.end_user.username,
                'password': self.end_user_password,
            }, secure=True)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'unauthorized_client')

        # Return 200 OK when trying password grant with a client with 'allow_oauth_password_grant' set to True
        client.allow_oauth_password_grant = True
        client.save()
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                'grant_type': 'password',
                'username': self.end_user.username,
                'password': self.end_user_password,
            }, secure=True)
        self.assertEqual(resp.status_code, 200)
        self.check_access_token_response_fields(resp)

        # Return 'invalid_client' when missing client_id
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                #'client_id': client.client_id,
                'grant_type': 'password',
                'username': self.end_user.username,
                'password': self.end_user_password,
            }, secure=True)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['error'], 'invalid_client')

        # Return 'invalid_client' when client_id does not exist in db
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': 'thi5i5aninv3nt3dcli3ntid',
                'grant_type': 'password',
                'username': self.end_user.username,
                'password': self.end_user_password,
            }, secure=True)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()['error'], 'invalid_client')

        # Return 'unsupported_grant_type' when grant type does not exist
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                'grant_type': 'invented_grant',
                'username': self.end_user.username,
                'password': self.end_user_password,
            }, secure=True)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'unsupported_grant_type')

        # Return 'invalid_request' when no username is provided
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                'grant_type': 'password',
                #'username': self.end_user.username,
                'password': self.end_user_password,
            }, secure=True)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'invalid_request')

        # Return 'invalid_request' when no password is provided
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                'grant_type': 'password',
                'username': self.end_user.username,
                #'password': self.end_user_password,
            }, secure=True)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'invalid_request')

    def test_oauth2_authorization_code_grant_flow(self):

        # Redirect to login page when visiting authorize page with an AnonymousUser
        client = ApiV2Client.objects.get(name='AuthorizationCodeClient')
        resp = self.client.get(
            reverse('oauth2_provider:authorize'),
            {
                'client_id': client.client_id,
                'response_type': 'code',
            }, secure=True, follow=True)
        response_path = resp.request['PATH_INFO']
        self.assertEqual(resp.status_code, 200)
        self.assertIn('/login', response_path)

        # Redirect includes 'error' param when using non-existing response type
        self.client.force_login(self.end_user)
        resp = self.client.get(
            reverse('oauth2_provider:authorize'),
            {
                'client_id': client.client_id,
                'response_type': 'non_existing_response_type',
            }, secure=True)
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(resp.request['PATH_INFO'] + '?' + resp.request['QUERY_STRING'], secure=True)
        self.assertTrue(resp.url.startswith(client.get_default_redirect_uri()))
        resp_params = self.get_params_from_url(resp.url)
        self.check_dict_has_fields(resp_params, ['error'])
        self.assertEqual(resp_params['error'], 'unsupported_response_type')

        # Redirect includes 'error' param when using non-supported response type
        resp = self.client.get(
            reverse('oauth2_provider:authorize'),
            {
                'client_id': client.client_id,
                'response_type': 'token',
            }, secure=True)
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(resp.request['PATH_INFO'] + '?' + resp.request['QUERY_STRING'], secure=True)
        self.assertEqual(resp.url.startswith(client.get_default_redirect_uri()), True)
        resp_params = self.get_params_from_url(resp.url)
        self.check_dict_has_fields(resp_params, ['error'])
        self.assertEqual(resp_params['error'], 'unauthorized_client')

        # Authorization page is displayed with errors with non-existing client_id
        resp = self.client.get(
            reverse('oauth2_provider:authorize'),
            {
                'client_id': 'thi5i5aninv3nt3dcli3ntid',
                'response_type': 'code',
            }, secure=True)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Invalid client_id parameter value', str(resp.content))

        #  Authorization page is displayed correctly when correct response_type and client_id
        resp = self.client.get(
            reverse('oauth2_provider:authorize'),
            {
                'client_id': client.client_id,
                'response_type': 'code',
            }, secure=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('name="allow" value="Authorize', str(resp.content))

        # Redirect includes 'code' and 'state' params
        resp = self.client.post(
            reverse('oauth2_provider:authorize'),
            {
                'client_id': client.client_id,
                'response_type': 'code',
                'redirect_uri': client.get_default_redirect_uri(),
                'scope': 'read',
                'state': 'an_optional_state',
                'allow': 'Authorize',
            }, secure=True)
        self.assertTrue(resp.url.startswith(client.get_default_redirect_uri()))
        resp_params = self.get_params_from_url(resp.url)
        self.assertEqual(resp_params['state'], 'an_optional_state')  # Check state is returned and preserved
        self.check_dict_has_fields(resp_params, ['code'])  # Check code is there

        # Return 200 OK when requesting access token setting client_id and client_secret in body params
        code = resp_params['code']
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                'client_secret': client.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': client.get_default_redirect_uri()
            }, secure=True)
        self.assertEqual(resp.status_code, 200)
        self.check_access_token_response_fields(resp)

        # Return bad request when trying to get access without client_secret
        resp = self.client.post(
            reverse('oauth2_provider:access_token'),
            {
                'client_id': client.client_id,
                #'client_secret': client.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': client.get_default_redirect_uri()
            }, secure=True)

        self.assertEqual(resp.status_code, 400)

    def test_token_authentication_with_header(self):
        user = User.objects.create_user("testuser")
        c = ApiV2Client(user=user, status='OK', redirect_uri="https://freesound.com",
                        url="https://freesound.com", name="test")
        c.save()
        headers = {
            'HTTP_AUTHORIZATION': f'Token {c.key}',
        }
        resp = self.client.get("/apiv2/", secure=True, **headers)
        self.assertEqual(resp.status_code, 200)

    def test_token_authentication_with_query_param(self):
        user = User.objects.create_user("testuser")
        c = ApiV2Client(user=user, status='OK', redirect_uri="https://freesound.com",
                        url="https://freesound.com", name="test")
        c.save()
        resp = self.client.get(f"/apiv2/?token={c.key}", secure=True)
        self.assertEqual(resp.status_code, 200)

    def test_token_authentication_disabled_client(self):
        user = User.objects.create_user("testuser")
        c = ApiV2Client(user=user, status='REV', redirect_uri="https://freesound.com",
                        url="https://freesound.com", name="test")
        c.save()
        resp = self.client.get(f"/apiv2/?token={c.key}", secure=True)
        self.assertEqual(resp.status_code, 401)

