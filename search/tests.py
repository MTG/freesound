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

from django.test import TestCase, override_settings
from django.urls import reverse
from sounds.models import Sound
from search.views import search_process_filter
from utils.search.solr import SolrResponseInterpreter, SolrResponseInterpreterPaginator
from utils.test_helpers import create_user_and_sounds
import mock
import copy


solr_select_returned_data = {
    'facet_counts': {
        'facet_dates': {},
        'facet_fields': {
            'bitdepth': ['16', 390, '24', 221, '0', 105, '32', 19, '4', 1],
            'bitrate': ['1411', 153, '1378', 151, '2250', 79, '1500', 32, '1536', 23],
            'channels': ['2', 630, '1', 91, '6', 12, '4', 4],
        },
        'facet_queries': {},
        'facet_ranges': {}
    },
    'grouped': {
        'grouping_pack': {
            'groups': [],  # Actual sounds to be returned are filled dynamically in tests
            'matches': 737,
            'ngroups': 548
        }
    },
    'responseHeader': {
        'QTime': 17,
        'params': {
            'f.grouping_pack.facet.limit': '10',
            'f.license.facet.limit': '10',
            'f.tag.facet.limit': '30',
            'f.username.facet.limit': '30',
            'facet': 'true',
            'facet.field': ['bitrate', 'bitdepth', 'channels'],
            'facet.limit': '5',
            'facet.mincount': '1',
            'facet.missing': 'false',
            'facet.sort': 'true',
            'fl': 'id',
            'group': 'true',
            'group.cache.percent': '0',
            'group.field': 'grouping_pack',
            'group.format': 'grouped',
            'group.limit': '1',
            'group.main': 'false',
            'group.ngroups': 'true',
            'group.offset': '0',
            'group.rows': '10',
            'group.start': '0',
            'group.truncate': 'false',
            'q': 'dogs',
            'qf': 'id^4 tag^4 description^3 username^1 pack_tokenized^2 original_filename^2',
            'qt': 'dismax',
            'rows': '15',
            'sort': 'score desc',
            'start': '0',
            'wt': 'json'
        },
        'status': 0
    }
}


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


class SearchPageTests(TestCase):

    fixtures = ['licenses', 'users', 'sounds_with_tags']

    def setUp(self):
        # Generate a fake solr response data to mock perform_solr_query function
        self.NUM_RESULTS = 15
        sound_ids = list(Sound.objects.filter(
            moderation_state="OK", processing_state="OK").values_list('id', flat=True)[:self.NUM_RESULTS])
        solr_select_returned_data['grouped']['grouping_pack']['groups'] = [
            {'doclist': {'docs': [{'id': sound_id}], 'numFound': 1, 'start': 0}, 'groupValue': str(sound_id)}
            for sound_id in sound_ids
        ]
        results = SolrResponseInterpreter(copy.deepcopy(solr_select_returned_data))
        # NOTE: in the line abve, we need to deepcopy the dictionary of results because SolrResponseInterpreter changes
        # it and makes it break when run a second time. Ideally SolrResponseInterpreter should be fixed so that it does
        # not change its input parameter.

        paginator = SolrResponseInterpreterPaginator(results, self.NUM_RESULTS)
        page = paginator.page(1)  # Get first page
        self.perform_solr_query_response = \
            (results.non_grouped_number_of_matches, results.facets, paginator, page, results.docs)

    @mock.patch('search.views.perform_solr_query')
    def test_search_page_response_ok(self, perform_solr_query):
        perform_solr_query.return_value = self.perform_solr_query_response

        # 200 response on sound search page access
        resp = self.client.get(reverse('sounds-search'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['error_text'], None)
        self.assertEqual(len(resp.context['docs']), self.NUM_RESULTS)

    @mock.patch('search.views.perform_solr_query')
    def test_search_page_num_queries(self, perform_solr_query):
        perform_solr_query.return_value = self.perform_solr_query_response

        # Check that we perform one single query to get all sounds' information and don't do one extra query per sound
        with self.assertNumQueries(1):
            self.client.get(reverse('sounds-search'))

    @mock.patch('search.views.perform_solr_query')
    def test_search_page_with_filters(self, perform_solr_query):
        perform_solr_query.return_value = self.perform_solr_query_response

        # 200 response on sound search page access
        resp = self.client.get(reverse('sounds-search'), {"f": 'grouping_pack:"Clutter" tag:"acoustic-guitar"'})
        self.assertEqual(resp.status_code, 200)

        # In this case we check if a non valid filter is applied it should be ignored.
        # grouping_pack it shouldn't be in filter_query_split, since is a not valid filter
        self.assertEqual(resp.context['filter_query_split'][0]['name'], 'tag:acoustic-guitar')
        self.assertEqual(len(resp.context['filter_query_split']), 1)

        resp = self.client.get(reverse('sounds-search'), {"f": 'grouping_pack:"19894_Clutter" tag:"acoustic-guitar"'})
        # Now we check if two valid filters are applied, then they are present in filter_query_split
        # Which means they are going to be displayed
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['filter_query_split']), 2)


class SearchProcessFilter(TestCase):

    def test_search_process_filter(self):

        filter_query = search_process_filter('ac_loudness: ac_dynamic_range: ac_temporal_centroid: ac_log_attack_time: '
                                             'ac_single_event: ac_tonality: ac_tonality_confidence: ac_loop: ac_tempo: '
                                             'ac_tempo_confidence: ac_note_midi: ac_note_name: ac_note_frequency: '
                                             'ac_note_confidence: ac_brightness: ac_depth: ac_hardness: ac_roughness: '
                                             'ac_boominess: ac_reverb: ac_warmth: ac_sharpness: another_field:')
        self.assertEqual(filter_query, 'ac_loudness_d: ac_dynamic_range_d: ac_temporal_centroid_d: '
                                       'ac_log_attack_time_d: ac_single_event_b: ac_tonality_s: '
                                       'ac_tonality_confidence_d: ac_loop_b: ac_tempo_i: ac_tempo_confidence_d: '
                                       'ac_note_midi_i: ac_note_name_s: ac_note_frequency_d: ac_note_confidence_d: '
                                       'ac_brightness_d: ac_depth_d: ac_hardness_d: ac_roughness_d: ac_boominess_d: '
                                       'ac_reverb_b: ac_warmth_d: ac_sharpness_d: another_field:')



class SearchResultClustering(TestCase):

    fixtures = ['licenses']

    def setUp(self):
        create_user_and_sounds(num_sounds=4, tags='tag1, tag2, tag3')
        sound_ids = list(Sound.objects.values_list('id', flat=True))

        self.successful_clustering_results = return_successful_clustering_results(*map(str, sound_ids))
        self.pending_clustering_results = pending_clustering_results
        self.failed_clustering_results = failed_clustering_results

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
        # context variable cluster_id_num_results: [(<cluster_id>, <num_sounds>, <tags>), ...]
        self.assertEqual(resp.context['cluster_id_num_results'], 
            [(0, 2, u'tag1 tag2 tag3'), (1, 2, u'tag1 tag2 tag3')])

    @mock.patch('search.views.cluster_sound_results')
    def test_pending_search_result_clustering_view(self, cluster_sound_results):
        cluster_sound_results.return_value = self.pending_clustering_results
        resp = self.client.get(reverse('clustering-facet'))

        # 200 status code & JSON response content
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {'status': 'pending'})

    @mock.patch('search.views.cluster_sound_results')
    def test_failed_search_result_clustering_view(self, cluster_sound_results):
        cluster_sound_results.return_value = self.failed_clustering_results
        resp = self.client.get(reverse('clustering-facet'))

        # 200 status code & JSON response content
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {'status': 'failed'})
