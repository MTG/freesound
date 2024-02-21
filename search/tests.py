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
from django.core.cache import cache
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.test.utils import skipIf, override_settings
from django.urls import reverse
from utils.search import search_query_processor
from sounds.models import Sound
from utils.search import SearchResults, SearchResultsPaginator
from utils.test_helpers import create_user_and_sounds
from utils.url import ComparableUrl
from unittest import mock
from django.contrib.auth.models import AnonymousUser


def create_fake_search_engine_results():
    return SearchResults(
        docs=[], # Actual sounds to be returned are filled dynamically in tests
        num_found=548,
        start=0,
        num_rows=0,
        non_grouped_number_of_results=737,
        facets={
            'bitdepth': [('16', 390), ('24', 221), ('0', 105), ('32', 19), ('4', 1)],
            'bitrate': [('1411', 153), ('1378', 151), ('2250', 79), ('1500', 32), ('1536', 23)],
            'channels': [('2', 630), ('1', 91), ('6', 12), ('4', 4)]},
        highlighting={},
        q_time=17
    )


def return_successful_clustering_results(sound_id_1, sound_id_2, sound_id_3, sound_id_4):
    return {
        'graph': {
            'directed': False,
            'graph': {

            },
            'nodes': [
                {
                    'group_centrality': 0.5,
                    'group': 0,
                    'id': sound_id_1
                },
                {
                    'group_centrality': 1,
                    'group': 0,
                    'id': sound_id_2
                },
                {
                    'group_centrality': 0.5,
                    'group': 1,
                    'id': sound_id_3
                },
                {
                    'group_centrality': 1,
                    'group': 1,
                    'id': sound_id_4
                },
            ],
            'links': [
                {
                    'source': sound_id_1,
                    'target': sound_id_2
                },
                {
                    'source': sound_id_1,
                    'target': sound_id_3
                },
                {
                    'source': sound_id_3,
                    'target': sound_id_4
                },
            ],
            'multigraph': False
        },
        'finished': True,
        'result': [
            [
                sound_id_1,
                sound_id_2
            ],
            [
                sound_id_3,
                sound_id_4
            ],
        ],
        'error':False
    }

pending_clustering_results = {'finished': False, 'error': False}

failed_clustering_results = {'finished': False, 'error': True}


def create_fake_perform_search_engine_query_response(num_results=15):
    # NOTE: this method needs Sound objects to have been created before running it (for example loading sounds_with_tags fixture)
    sound_ids = list(Sound.objects.filter(
        moderation_state="OK", processing_state="OK").values_list('id', 'pack_id')[:num_results])
    results = create_fake_search_engine_results()
    results.docs = [
        {'group_docs': [{'id': sound_id}],
         'id': sound_id,
         'n_more_in_group': 0,
         'group_name': f'{pack_id}_xyz' if pack_id is not None else str(sound_id)} for sound_id, pack_id in sound_ids
    ]
    paginator = SearchResultsPaginator(results, num_results)
    return (results, paginator)
    

class SearchPageTests(TestCase):

    fixtures = ['licenses', 'users', 'sounds_with_tags']

    def setUp(self):
        # Generate a fake solr response data to mock perform_search_engine_query function
        self.NUM_RESULTS = 15
        self.perform_search_engine_query_response = create_fake_perform_search_engine_query_response(self.NUM_RESULTS)

    @mock.patch('search.views.perform_search_engine_query')
    def test_search_page_response_ok(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response

        # 200 response on sound search page access
        resp = self.client.get(reverse('sounds-search'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['error_text'], None)
        self.assertEqual(len(resp.context['docs']), self.NUM_RESULTS)


    @mock.patch('search.views.perform_search_engine_query')
    def test_search_page_num_queries(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response

        # Check that we perform one single query to get all sounds' information and don't do one extra query per sound
        cache.clear()
        with self.assertNumQueries(1):
            self.client.get(reverse('sounds-search'))

        # Repeat the check when using the "grid display"
        cache.clear()
        with self.assertNumQueries(1):
            self.client.get(reverse('sounds-search') + '?cm=1')
       
        with override_settings(USE_SEARCH_ENGINE_SIMILARITY=True):
            # When using search engine similarity, there'll be one extra query performed to get the similarity status of the sounds

            # Now check number of queries when displaying results as packs (i.e., searching for packs)
            cache.clear()
            with self.assertNumQueries(6):
                self.client.get(reverse('sounds-search') + '?dp=1')

            # Also check packs when displaying in grid mode
            cache.clear()
            with self.assertNumQueries(6):
                self.client.get(reverse('sounds-search') + '?dp=1&cm=1')

        with override_settings(USE_SEARCH_ENGINE_SIMILARITY=False):
            # When not using search engine similarity, there'll be one less query performed as similarity state is retrieved directly from sound object

            # Now check number of queries when displaying results as packs (i.e., searching for packs)
            cache.clear()
            with self.assertNumQueries(5):
                self.client.get(reverse('sounds-search') + '?dp=1')

            # Also check packs when displaying in grid mode
            cache.clear()
            with self.assertNumQueries(5):
                self.client.get(reverse('sounds-search') + '?dp=1&cm=1')

    @mock.patch('search.views.perform_search_engine_query')
    def test_search_page_with_filters(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response

        # 200 response on sound search page access
        resp = self.client.get(reverse('sounds-search'), {"f": 'grouping_pack:"Clutter" tag:"acoustic-guitar"'})
        self.assertEqual(resp.status_code, 200)

        # In this case we check if a non valid filter is applied it should be ignored.
        # grouping_pack it shouldn't be in filter_query_split, since is a not valid filter
        self.assertEqual(resp.context['filter_query_split'][0]['name'], 'tag:"acoustic-guitar"')
        self.assertEqual(len(resp.context['filter_query_split']), 1)

        resp = self.client.get(reverse('sounds-search'), {"f": 'grouping_pack:"19894_Clutter" tag:"acoustic-guitar"'})
        # Now we check if two valid filters are applied, then they are present in filter_query_split
        # Which means they are going to be displayed
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['filter_query_split']), 2)


class SearchResultClustering(TestCase):

    fixtures = ['licenses']

    def setUp(self):
        _, _, sounds = create_user_and_sounds(num_sounds=4, tags='tag1, tag2, tag3')
        sound_ids = []
        sound_id_preview_urls = []
        for sound in sounds:
            sound_ids.append(str(sound.id))
            sound_id_preview_urls.append((sound.id, sound.locations()['preview']['LQ']['ogg']['url']))

        self.sound_id_preview_urls = sound_id_preview_urls
        self.successful_clustering_results = return_successful_clustering_results(*sound_ids)
        self.pending_clustering_results = pending_clustering_results
        self.failed_clustering_results = failed_clustering_results

    @skipIf(True, "Clustering not yet enabled in BW")
    @mock.patch('search.views.cluster_sound_results')
    def test_successful_search_result_clustering_view(self, cluster_sound_results):
        cluster_sound_results.return_value = self.successful_clustering_results
        resp = self.client.get(reverse('clustering-facet'))

        # 200 status code & use of clustering facets template
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'search/clustering_facet.html')

        # check cluster's content
        # 2 sounds per clusters
        # 3 most used tags in the cluster 'tag1 tag2 tag3'
        # context variable cluster_id_num_results_tags_sound_examples: [(<cluster_id>, <num_sounds>, <tags>, <ids_preview_urls>), ...]
        self.assertEqual(resp.context['cluster_id_num_results_tags_sound_examples'], [
            (0, 2, 'tag1 tag2 tag3', self.sound_id_preview_urls[:2]), 
            (1, 2, 'tag1 tag2 tag3', self.sound_id_preview_urls[2:])
        ])

    @skipIf(True, "Clustering not yet enabled in BW")
    @mock.patch('search.views.cluster_sound_results')
    def test_pending_search_result_clustering_view(self, cluster_sound_results):
        cluster_sound_results.return_value = self.pending_clustering_results
        resp = self.client.get(reverse('clustering-facet'))

        # 200 status code & JSON response content
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {'status': 'pending'})

    @skipIf(True, "Clustering not yet enabled in BW")
    @mock.patch('search.views.cluster_sound_results')
    def test_failed_search_result_clustering_view(self, cluster_sound_results):
        cluster_sound_results.return_value = self.failed_clustering_results
        resp = self.client.get(reverse('clustering-facet'))

        # 200 status code & JSON response content
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {'status': 'failed'})


class SearchQueryProcessorTests(TestCase):

    default_expected_params = {
        'current_page': 1,
        'facets': settings.SEARCH_SOUNDS_DEFAULT_FACETS,
        'field_list': ['id', 'score'],
        'group_by_pack': True,
        'num_sounds': settings.SOUNDS_PER_PAGE,
        'num_sounds_per_pack_group': 1,
        'only_sounds_with_pack': False,
        'only_sounds_within_ids': [],
        'query_fields': settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS,
        'query_filter': '',
        'similar_to': None,
        'sort': settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,  # Empty query should sort by date added, so use this as expected default
        'textual_query': ''}

    def setUp(self):
        self.factory = RequestFactory()
        self.maxDiff = None

    def assertExpectedParams(self, returned_query_params, specific_expected_params={}):    
        dict_to_compare = self.default_expected_params.copy()
        dict_to_compare.update(specific_expected_params)
        self.assertDictEqual(returned_query_params, dict_to_compare)

    def assertGetUrlAsExpected(self, sqp, expected_url):
        sqp_url = sqp.get_url()
        self.assertEqual(ComparableUrl(sqp_url), ComparableUrl(expected_url))

    def run_fake_search_query_processor(self, base_url=reverse('sounds-search'), url=None, params={}, user=AnonymousUser()):
        if url is None:
            request = self.factory.get(base_url, params)
        else:
            request = self.factory.get(url)
        request.user = user
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
        sqp, _ = self.run_fake_search_query_processor(params={'s': settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC})
        self.assertExpectedParams(sqp.as_query_params(), {'sort': settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC})
        self.assertGetUrlAsExpected(sqp, '/search/')

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
        sqp, url = self.run_fake_search_query_processor(params={'a_tag': '1', 'a_description': '1', 'a_soundid': '0'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_fields': {
            settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_DESCRIPTION], 
            settings.SEARCH_SOUNDS_FIELD_TAGS: settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_TAGS]
        }})
        self.assertGetUrlAsExpected(sqp, url.replace('a_soundid=0', ''))  # Here we remove a_soundid from the expected URL because sqp.get_url() will exclude it as value is not '1'

        # With custom field weights specified
        sqp, url = self.run_fake_search_query_processor(params={'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_fields': {
            settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: 2, 
            settings.SEARCH_SOUNDS_FIELD_ID: 1
        }})
        self.assertGetUrlAsExpected(sqp, url)

        # With custom field weights specified AND search in
        sqp, url = self.run_fake_search_query_processor(params={'a_soundid': '1', 'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
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
        expected_facets = settings.SEARCH_SOUNDS_DEFAULT_FACETS.copy()
        expected_facets['tags']['limit'] = 50
        self.assertExpectedParams(sqp.as_query_params(), {'facets': expected_facets})
        self.assertGetUrlAsExpected(sqp, url)

        # With cluster id option
        with override_settings(ENABLE_SEARCH_RESULTS_CLUSTERING=True):
            fake_get_ids_in_cluster.return_value = [1, 2 ,3, 4]  # Mock the response of get_ids_in_cluster
            sqp, url = self.run_fake_search_query_processor(params={'cid': '31'})
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
        sqp, url = self.run_fake_search_query_processor(params={'f': 'grouping_pack:"19894_Clutter"'})
        self.assertExpectedParams(sqp.as_query_params(), {'query_filter': 'grouping_pack:"19894_Clutter"', 'group_by_pack': False})
        self.assertGetUrlAsExpected(sqp, url)
         

    def test_search_query_processor_disabled_options(self):
        # Test that some search options are marked as disabled depending on the state of some other options
        # NOTE: disabled state is used when displaying the options in the UI, but has no other effects
        
        # query if similarity on
        sqp, _ = self.run_fake_search_query_processor(params={'st': '1234'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionQuery.name].disabled)
        
        # sort if similarity on
        sqp, _ = self.run_fake_search_query_processor(params={'st': '1234'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionSort.name].disabled)

        # group_by_pack if display_as_packs or map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'dp': '1'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionGroupByPack.name].disabled)
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionGroupByPack.name].disabled)

        # display as packs if map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionDisplayResultsAsPacks.name].disabled)

        # grid_mode if map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionGridMode.name].disabled)

        # is_geotagged if map_mode
        sqp, _ = self.run_fake_search_query_processor(params={'mm': '1'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionIsGeotagged.name].disabled)

        # search_in if tags_mode or similar_to_mode
        sqp, _ = self.run_fake_search_query_processor(params={'st': '1'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionSearchIn.name].disabled)
        sqp, _ = self.run_fake_search_query_processor(base_url=reverse('tags'))
        self.assertTrue(sqp.options[search_query_processor.SearchOptionSearchIn.name].disabled) 

        # group_by_pack and display_as_packs if filter contains a pack
        sqp, _ = self.run_fake_search_query_processor(params={'f': 'grouping_pack:"19894_Clutter"'})
        self.assertTrue(sqp.options[search_query_processor.SearchOptionGroupByPack.name].disabled) 
        self.assertTrue(sqp.options[search_query_processor.SearchOptionDisplayResultsAsPacks.name].disabled) 
        
    def test_search_query_processor_tags_in_filter(self):
        sqp, _ = self.run_fake_search_query_processor(params={
            'f': 'duration:[0.25 TO 20] tag:"tag1" is_geotagged:1 (id:1 OR id:2 OR id:3) tag:"tag2" (tag:"tag3" OR tag:"tag4")',
        })
        self.assertEqual(sorted(sqp.get_tags_in_filter()), sorted(['tag1', 'tag2']))

        sqp, _ = self.run_fake_search_query_processor(params={
            'f': 'duration:[0.25 TO 20] is_geotagged:1 (id:1 OR id:2 OR id:3)',
        })
        self.assertEqual(sqp.get_tags_in_filter(), [])

    def test_search_query_processor_make_url_add_remove_filters(self):
        # Test add_filters adds them to the URL
        sqp, _ = self.run_fake_search_query_processor()
        self.assertEqual(sqp.get_url(add_filters=['tag:"tag1"']), '/search/?f=tag%3A%22tag1%22')

        # Test remove_filters removes them from the URL
        sqp, _ = self.run_fake_search_query_processor(params={'f': 'filter1:"aaa" filter2:123'})
        self.assertEqual(sqp.get_url(remove_filters=['filter1:"aaa"', 'filter2:123']), '/search/')

    def test_earch_query_processor_contains_active_advanced_search_options(self):
         # Query with no params
        sqp, _ = self.run_fake_search_query_processor()
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # Empty query
        sqp, _ = self.run_fake_search_query_processor(params={'q': ''})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # Empty query with sorting specifyied
        sqp, _ = self.run_fake_search_query_processor(params={'s': settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # Basic query with only text
        sqp, _ = self.run_fake_search_query_processor(params={'q':'test'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # With page number specified
        sqp, _ = self.run_fake_search_query_processor(params={'page': '3'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), False)
        
        # With "search in" options specified
        sqp, _ = self.run_fake_search_query_processor(params={'a_tag': '1', 'a_description': '1', 'a_soundid': '0'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        
        # With custom field weights specified
        sqp, _ = self.run_fake_search_query_processor(params={'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
        self.assertEqual(sqp.contains_active_advanced_search_options(), True)
        
        # With custom field weights specified AND search in
        sqp, _ = self.run_fake_search_query_processor(params={'a_soundid': '1', 'w': f'{settings.SEARCH_SOUNDS_FIELD_DESCRIPTION}:2,{settings.SEARCH_SOUNDS_FIELD_ID}:1'})
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
        