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

from django.core.cache import cache
from django.test import TestCase
from django.test.utils import skipIf
from django.urls import reverse
from sounds.models import Sound
from utils.search import SearchResults, SearchResultsPaginator
from utils.test_helpers import create_user_and_sounds
from unittest import mock


def create_fake_search_engine_results():
    return SearchResults(
        docs=[],    # Actual sounds to be returned are filled dynamically in tests
        num_found=548,
        start=0,
        num_rows=0,
        non_grouped_number_of_results=737,
        facets={
            'bitdepth': [('16', 390), ('24', 221), ('0', 105), ('32', 19), ('4', 1)],
            'bitrate': [('1411', 153), ('1378', 151), ('2250', 79), ('1500', 32), ('1536', 23)],
            'channels': [('2', 630), ('1', 91), ('6', 12), ('4', 4)]
        },
        highlighting={},
        q_time=17
    )


def return_successful_clustering_results(sound_id_1, sound_id_2, sound_id_3, sound_id_4):
    return {
        'graph': {
            'directed': False,
            'graph': {},
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
            [sound_id_1, sound_id_2],
            [sound_id_3, sound_id_4],
        ],
        'error': False
    }


pending_clustering_results = {'finished': False, 'error': False}

failed_clustering_results = {'finished': False, 'error': True}


def create_fake_perform_search_engine_query_response(num_results=15):
    # NOTE: this method needs Sound objects to have been created before running it (for example loading sounds_with_tags fixture)
    sound_ids = list(
        Sound.objects.filter(moderation_state="OK", processing_state="OK").values_list('id', 'pack_id')[:num_results]
    )
    results = create_fake_search_engine_results()
    results.docs = [{
        'group_docs': [{
            'id': sound_id
        }],
        'id': sound_id,
        'n_more_in_group': 0,
        'group_name': f'{pack_id}_xyz' if pack_id is not None else str(sound_id)
    } for sound_id, pack_id in sound_ids]
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

        # Now check number of queries when displaying results as packs (i.e., searching for packs)
        cache.clear()
        with self.assertNumQueries(5):
            self.client.get(reverse('sounds-search') + '?only_p=1')

        # Also check packs when displaying in grid mode
        cache.clear()
        with self.assertNumQueries(5):
            self.client.get(reverse('sounds-search') + '?only_p=1&cm=1')

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
        self.assertEqual(
            resp.context['cluster_id_num_results_tags_sound_examples'],
            [(0, 2, 'tag1 tag2 tag3', self.sound_id_preview_urls[:2]),
             (1, 2, 'tag1 tag2 tag3', self.sound_id_preview_urls[2:])]
        )

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
