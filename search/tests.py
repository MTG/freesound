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
from utils.search.solr import SolrResponseInterpreter, SolrResponseInterpreterPaginator, SolrQuery
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


class SearchPageTests(TestCase):

    fixtures = ['users', 'sounds_with_tags']

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

    def test_search_filter(self):
        # Test conversion of the filter_query, it should add the '+' sign to each filter value
        query = SolrQuery()
        filter_query = "created:[* TO NOW]"
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], "+created:[* TO NOW]")

        filter_query = 'tag:bass description:"heavy distortion"'
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], '+tag:bass +description:"heavy distortion"')

        filter_query = 'tag:bass tag:music'
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], '+tag:bass +tag:music')

        filter_query = 'tag:bass +is_geotagged:true'
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], '+tag:bass +is_geotagged:true')

        filter_query = '+tag:bass is_geotagged:true'
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], '+tag:bass +is_geotagged:true')

        filter_query = "is_geotagged:true tag:field-recording duration:[0 TO 120]"
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], "+is_geotagged:true +tag:field-recording +duration:[0 TO 120]")

        filter_query = "is_geotagged:true {!geofilt sfield=geotag pt=41.3833,2.1833 d=10}"
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], "+is_geotagged:true +{!geofilt sfield=geotag pt=41.3833,2.1833 d=10}")

        filter_query = "{!geofilt sfield=geotag pt=41.3833,2.1833 d=10} tag:barcelona"
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], "+{!geofilt sfield=geotag pt=41.3833,2.1833 d=10} +tag:barcelona")

        # If the filter contains OR operator then don't replace
        filter_query = "is_geotagged:true OR tag:field-recording"
        query.set_query_options(field_list=["id"], filter_query=filter_query)
        self.assertEqual(query.params['fq'], filter_query)
