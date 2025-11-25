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
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.urls import reverse
from utils.search import search_query_processor
from utils.url import ComparableUrl
from unittest import mock


class SearchQueryProcessorTests(TestCase):

    default_expected_params = {
        'current_page': 1,
        'facets': settings.SEARCH_SOUNDS_DEFAULT_FACETS | settings.SEARCH_SOUNDS_BETA_FACETS,  # Combine all facets because we normally test with superuser,
        'field_list': ['id', 'score'],
        'group_by_pack': True,
        'num_sounds': settings.SOUNDS_PER_PAGE,
        'num_sounds_per_pack_group': 1,
        'only_sounds_with_pack': False,
        'only_sounds_within_ids': [],
        'query_fields': settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS,
        'query_filter': '',
        'similar_to': None,
        'similar_to_similarity_space': settings.SIMILARITY_SPACE_DEFAULT,
        'sort': settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,  # Empty query should sort by date added, so use this as expected default
        'textual_query': ''}

    def setUp(self):
        self.factory = RequestFactory()
        self.maxDiff = None
        self.user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
        self.user.is_superuser = True
        self.user.save()

    def assertExpectedParams(self, returned_query_params, specific_expected_params={}):    
        dict_to_compare = self.default_expected_params.copy()
        dict_to_compare.update(specific_expected_params)
        self.assertDictEqual(returned_query_params, dict_to_compare)

    def assertGetUrlAsExpected(self, sqp, expected_url):
        sqp_url = sqp.get_url()
        self.assertEqual(ComparableUrl(sqp_url), ComparableUrl(expected_url))

    def run_fake_search_query_processor(self, base_url=reverse('sounds-search'), url=None, params={}, user=None):
        if url is None:
            request = self.factory.get(base_url, params)
        else:
            request = self.factory.get(url)
        request.user = user if user is not None else self.user
        return search_query_processor.SearchQueryProcessor(request), request.get_full_path()

    @mock.patch('utils.search.search_query_processor.get_ids_in_cluster')
    def test_search_query_processor_as_query_params_and_make_url(self, fake_get_ids_in_cluster):
        # This will test that the SearchQueryProcessor correctly processes the request parameters and generates the
        # expected query_params object to be sent to a SearchEngine object. Also it tests that once SearchQueryProcessor
        # has loaded parameters from the request, it is able to generate URLs which are equivalent to the original request.
        
        # Query with no params, all should be default behaviour (sorting by date added)
        sqp, url = self.run_fake_search_query_processor()
        self.assertExpectedParams(sqp.as_query_params())
        self.assertGetUrlAsExpected(sqp, url)

        # Empty query with no sorting specified, will sort by date added just like query with no params at all
        sqp, url = self.run_fake_search_query_processor(params={'q': ''})
        self.assertExpectedParams(sqp.as_query_params())
        self.assertGetUrlAsExpected(sqp, url)

        # Empty query with sorting specified, will sort as indicated
        sqp, url = self.run_fake_search_query_processor(params={'s': settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC})
        self.assertExpectedParams(sqp.as_query_params(), {'sort': settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC})
        self.assertGetUrlAsExpected(sqp, url)

        # Basic query with only text, results should be sorted by score
        sqp, url = self.run_fake_search_query_processor(params={'q':'test'})
        self.assertExpectedParams(sqp.as_query_params(), {'textual_query': 'test',
                                                          'sort': settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC})
        self.assertGetUrlAsExpected(sqp, url)
        
        # With page number specified
        sqp, url = self.run_fake_search_query_processor(params={'page': '3'})
        self.assertExpectedParams(sqp.as_query_params(), {'current_page': 3})
        self.assertGetUrlAsExpected(sqp, url)

        # With "search in" options specified
        sqp, url = self.run_fake_search_query_processor(params={'si_tags': '1', 'si_description': '1', 'si_sound_id': '0'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_fields': {
            settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_DESCRIPTION], 
            settings.SEARCH_SOUNDS_FIELD_TAGS: settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_TAGS]
        }})
        self.assertGetUrlAsExpected(sqp, url.replace('si_sound_id=0', ''))  # Here we remove a_soundid from the expected URL because sqp.get_url() will exclude it as value is not '1'

        # With custom field weights specified
        sqp, url = self.run_fake_search_query_processor(params={'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_fields': {
            settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: 2, 
            settings.SEARCH_SOUNDS_FIELD_ID: 1
        }})
        self.assertGetUrlAsExpected(sqp, url)

        # With custom field weights specified AND search in
        sqp, url = self.run_fake_search_query_processor(params={'si_sound_id': '1', 'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_fields': {
            settings.SEARCH_SOUNDS_FIELD_ID: 1
        }})
        self.assertGetUrlAsExpected(sqp, url)

        # With duration filter
        sqp, url = self.run_fake_search_query_processor(params={'d0': '0.25', 'd1': '2.05'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': 'duration:[0.25 TO 2.05]'})
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor(params={'d0': '0.25'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': 'duration:[0.25 TO *]'})
        self.assertGetUrlAsExpected(sqp, url + '&d1=*')  # Add d1 to the expected url as sqp will add it
        sqp, url = self.run_fake_search_query_processor(params={'d1': '0.25'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': 'duration:[0 TO 0.25]'})
        self.assertGetUrlAsExpected(sqp, url + '&d0=0')  # Add d0 to the expected url as sqp will add it

        # With geotag filter
        sqp, url = self.run_fake_search_query_processor(params={'ig': '1'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': 'is_geotagged:1'})
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor(params={'ig': '0'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': ''})  # If geotagged option is 0, no filter should be added
        self.assertGetUrlAsExpected(sqp, '/search/')  # URL should not include ig=0 as this is the default value

        # With remix filter
        sqp, url = self.run_fake_search_query_processor(params={'r': '1'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': 'in_remix_group:1'})
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor(params={'r': '0'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': ''})  # If remix option is 0, no filter should be added
        self.assertGetUrlAsExpected(sqp, '/search/')  # URL should not include r=0 as this is the default value

        # With group by pack option (defaults to True)
        sqp, url = self.run_fake_search_query_processor(params={'g': '1'})
        self.assertExpectedParams(sqp.as_query_params(), {'group_by_pack': True})
        self.assertGetUrlAsExpected(sqp, '/search/')  # URL should not include g=1 as this is the default value
        sqp, url = self.run_fake_search_query_processor(params={'g': '0'})
        self.assertExpectedParams(sqp.as_query_params(), {'group_by_pack': False})
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor()
        self.assertExpectedParams(sqp.as_query_params(), {'group_by_pack': True})
        self.assertGetUrlAsExpected(sqp, url)

         # With display results as packs option
        sqp, url = self.run_fake_search_query_processor(params={'dp': '1'})
        self.assertExpectedParams(sqp.as_query_params(), {'group_by_pack': True, 'only_sounds_with_pack': True, 'num_sounds_per_pack_group': 3})
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor(params={'dp': '1', 'g': '0'}) # When display packs is enabled, always group by pack
        self.assertExpectedParams(sqp.as_query_params(), {'group_by_pack': True, 'only_sounds_with_pack': True, 'num_sounds_per_pack_group': 3})
        self.assertGetUrlAsExpected(sqp, url)

        # With compact mode option
        sqp, url = self.run_fake_search_query_processor(params={'cm': '1'})
        self.assertExpectedParams(sqp.as_query_params(), {'num_sounds': settings.SOUNDS_PER_PAGE_COMPACT_MODE })
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor(params={'cm': '1', 'dp': '1'})  # In display pack mode, number of sounds stays the same
        self.assertExpectedParams(sqp.as_query_params(), {'num_sounds': settings.SOUNDS_PER_PAGE, 
                                                          'only_sounds_with_pack': True, 
                                                          'num_sounds_per_pack_group': 3})
        self.assertGetUrlAsExpected(sqp, url)

        # With map mode option
        sqp, url = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertExpectedParams(sqp.as_query_params(), {'group_by_pack': False, 
                                                          'num_sounds': settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,
                                                          'query_filter': 'is_geotagged:1',
                                                          'field_list': ['id', 'score', 'geotag']})
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor(params={'mm': '1', 'page': '3'})  # Page number in map mode is always 1
        self.assertExpectedParams(sqp.as_query_params(), {'group_by_pack': False, 
                                                          'num_sounds': settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,
                                                          'query_filter': 'is_geotagged:1',
                                                          'field_list': ['id', 'score', 'geotag']})
        self.assertGetUrlAsExpected(sqp, url)
        
        # With tags mode
        sqp, url = self.run_fake_search_query_processor(base_url=reverse('tags'))
        expected_facets = settings.SEARCH_SOUNDS_DEFAULT_FACETS | settings.SEARCH_SOUNDS_BETA_FACETS
        expected_facets['tags']['limit'] = 50
        self.assertExpectedParams(sqp.as_query_params(), {'facets': expected_facets})
        self.assertGetUrlAsExpected(sqp, url)

        # With cluster id option
        fake_get_ids_in_cluster.return_value = [1, 2 ,3, 4]  # Mock the response of get_ids_in_cluster
        sqp, url = self.run_fake_search_query_processor(params={'cid': '31', 'cc': '1'})
        self.assertExpectedParams(sqp.as_query_params(), {'only_sounds_within_ids': [1, 2 ,3, 4]})
        self.assertGetUrlAsExpected(sqp, url)

        # With similar to option
        sqp, url = self.run_fake_search_query_processor(params={'st': '1234'})  # Passing similarity target as sound ID
        self.assertExpectedParams(sqp.as_query_params(), {'similar_to': 1234})
        self.assertGetUrlAsExpected(sqp, url)
        sqp, url = self.run_fake_search_query_processor(params={'st': '[1.34,3.56,5.78]'})  # Passing similarity target as sound ID
        self.assertExpectedParams(sqp.as_query_params(), {'similar_to': [1.34, 3.56, 5.78]})
        self.assertGetUrlAsExpected(sqp, url)

        # Using a pack filter, sounds should not be grouped by pack
        sqp, url = self.run_fake_search_query_processor(params={'f': 'pack_grouping:"19894_Clutter"'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': 'pack_grouping:"19894_Clutter"', 'group_by_pack': False})
        self.assertGetUrlAsExpected(sqp, url)
         
    def test_search_query_processor_disabled_options(self):
        # Test that some search options are marked as disabled depending on the state of some other options
        # NOTE: disabled state is used when displaying the options in the UI, but has no other effects
        
        # query if similarity on
        sqp, _ = self.run_fake_search_query_processor(params={'st': '1234'})
        self.assertTrue(sqp.options['query'].disabled)
        
        # sort if similarity on
        sqp, _ = self.run_fake_search_query_processor(params={'st': '1234'})
        self.assertTrue(sqp.options['sort_by'].disabled)

        # group_by_pack if display_as_packs or map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'dp': '1'})
        self.assertTrue(sqp.options['group_by_pack'].disabled)
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options['group_by_pack'].disabled)

        # display as packs if map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options['display_as_packs'].disabled)

        # grid_mode if map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options['grid_mode'].disabled)

        # is_geotagged if map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options['is_geotagged'].disabled)

        # search_in if tags_mode or similar_to_mode
        sqp, _ = self.run_fake_search_query_processor(params={'st': '1'})
        self.assertTrue(sqp.options['search_in'].disabled)
        sqp, _ = self.run_fake_search_query_processor(base_url=reverse('tags'))
        self.assertTrue(sqp.options['search_in'].disabled) 

        # group_by_pack and display_as_packs if filter contains a pack
        sqp, _ = self.run_fake_search_query_processor(params={'f': 'pack_grouping:"19894_Clutter"'})
        self.assertTrue(sqp.options['group_by_pack'].disabled) 
        self.assertTrue(sqp.options['display_as_packs'].disabled) 
        
    def test_search_query_processor_tags_in_filter(self):
        sqp, _ = self.run_fake_search_query_processor(params={
            'f': 'duration:[0.25 TO 20] tag:"tag1" is_geotagged:1 (id:1 OR id:2 OR id:3) tag:"tag2" (tag:"tag3" OR tag:"tag4")',
        })
        self.assertEqual(sorted(sqp.get_tags_in_filters()), sorted(['tag1', 'tag2']))

        sqp, _ = self.run_fake_search_query_processor(params={
            'f': 'duration:[0.25 TO 20] is_geotagged:1 (id:1 OR id:2 OR id:3)',
        })
        self.assertEqual(sqp.get_tags_in_filters(), [])

    def test_search_query_processor_make_url_add_remove_filters(self):
        # Test add_filters adds them to the URL
        sqp, _ = self.run_fake_search_query_processor()
        self.assertEqual(sqp.get_url(add_filters=['tag:"tag1"']), '/search/?f=tag%3A%22tag1%22')

        # Test remove_filters removes them from the URL
        sqp, _ = self.run_fake_search_query_processor(params={'f': 'filter1:"aaa" filter2:123'})
        self.assertEqual(sqp.get_url(remove_filters=['filter1:"aaa"', 'filter2:123']), '/search/')

    def test_search_query_processor_contains_active_advanced_search_options(self):
         # Query with no params
        sqp, _ = self.run_fake_search_query_processor()
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # Empty query
        sqp, _ = self.run_fake_search_query_processor(params={'q': ''})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # Empty query with sorting specified
        sqp, _ = self.run_fake_search_query_processor(params={'s': settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # Basic query with only text
        sqp, _ = self.run_fake_search_query_processor(params={'q':'test'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # With page number specified
        sqp, _ = self.run_fake_search_query_processor(params={'page': '3'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # With "search in" options specified
        sqp, _ = self.run_fake_search_query_processor(params={'si_tags': '1', 'si_description': '1', 'si_sound_id': '0'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        
        # With custom field weights specified
        sqp, _ = self.run_fake_search_query_processor(params={'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        
        # With custom field weights specified AND search in
        sqp, _ = self.run_fake_search_query_processor(params={'si_sound_id': '1', 'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)

        # With duration filter
        sqp, _ = self.run_fake_search_query_processor(params={'d0': '0.25', 'd1': '2.05'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        sqp, _ = self.run_fake_search_query_processor(params={'d0': '0', 'd1': '*'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # False if parameters are default
        
        # With geotag filter
        sqp, _ = self.run_fake_search_query_processor(params={'ig': '1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        sqp, _ = self.run_fake_search_query_processor(params={'ig': '0'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # False if parameters are default
        
        # With remix filter
        sqp, _ = self.run_fake_search_query_processor(params={'r': '1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        sqp, _ = self.run_fake_search_query_processor(params={'r': '0'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # False if parameters are default
        
        # With group by pack option (defaults to True)
        sqp, _ = self.run_fake_search_query_processor(params={'g': '0'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        sqp, _ = self.run_fake_search_query_processor(params={'g': '1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # False if parameters are default

         # With display results as packs option
        sqp, _ = self.run_fake_search_query_processor(params={'dp': '1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # Not considered an active filter
        
        # With compact mode option
        sqp, _ = self.run_fake_search_query_processor(params={'cm': '1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # Not considered an active filter
        
        # With map mode option
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # Not considered an active filter
        
        # With tags mode
        sqp, _ = self.run_fake_search_query_processor(base_url=reverse('tags'))
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # Not considered an active filter
        
        # With cluster id
        sqp, _ = self.run_fake_search_query_processor(params={'cid': '31'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)  # Clustering not an advanced search option
        
        # With similar to option
        sqp, _ = self.run_fake_search_query_processor(params={'st': '1234'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)

    def test_search_query_processor_as_query_params_exclude_facet_filters(self):
        for filter_name, is_facet in [
            ('samplerate', True),
            ('pack_grouping', True),
            ('username', True),
            ('tags', True),
            ('bitrate', True),
            ('bitdepth', True),
            ('type', True),
            ('channels', True),
            ('license', True),
            ('non_facet_filter', False),
        ]:
            sqp, _ = self.run_fake_search_query_processor(params={'f': f'{filter_name}:123'})
            self.assertEqual(f'{filter_name}:123' in sqp.as_query_params(exclude_facet_filters=True)['query_filter'], not is_facet)
            self.assertEqual(f'{filter_name}:123' in sqp.as_query_params(exclude_facet_filters=False)['query_filter'], True)


    def test_search_query_processor_as_query_params_special_chars(self):
        # Special chars in query
        query = 'Æ æ ¿ É'
        sqp, _ = self.run_fake_search_query_processor(params={'q': query})
        self.assertEqual(sqp.as_query_params()['textual_query'], query)

        # Special chars in filter
        flt = 'pack_grouping:"32119_Conch Blowing (शङ्ख)"'
        sqp, _ = self.run_fake_search_query_processor(params={'f': flt})
        self.assertEqual(sqp.as_query_params()['query_filter'], flt)

        flt = 'license:"sampling+"'
        sqp, _ = self.run_fake_search_query_processor(params={'f': flt})
        self.assertEqual(sqp.as_query_params()['query_filter'], flt)
