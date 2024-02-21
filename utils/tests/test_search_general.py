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
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from django.conf import settings
from urllib.parse import quote_plus
from utils.search.search_sounds import remove_facet_filters
from utils.search.lucene_parser import parse_query_filter_string


class SearchUtilsTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_remove_facet_filters(self):
        query_filter_str = 'is_geotagged:1 tag:"dog"'
        parsed_filters = parse_query_filter_string(query_filter_str)
        filter_without_facet, has_facet_filter = remove_facet_filters(parsed_filters)
        self.assertTrue(has_facet_filter)
        self.assertEqual(filter_without_facet, 'is_geotagged:1')

    def test_remove_facet_filters_no_facet(self):
        query_filter_str = 'duration:[1 TO 10] is_geotagged:1'
        parsed_filters = parse_query_filter_string(query_filter_str)
        filter_without_facet, has_facet_filter = remove_facet_filters(parsed_filters)
        self.assertFalse(has_facet_filter)
        self.assertEqual(filter_without_facet, query_filter_str)

    def test_remove_facet_filters_special_char(self):
        query_filter_str = 'grouping_pack:"1_:)" tag:"dog"'
        parsed_filters = parse_query_filter_string(query_filter_str)
        filter_without_facet, has_facet_filter = remove_facet_filters(parsed_filters)
        self.assertTrue(has_facet_filter)
        self.assertEqual(filter_without_facet, '')

    def test_remove_facet_filters_special_char2(self):
        query_filter_str = 'grouping_pack:"19265_Impacts, Hits, Friction & Tools" tag:"tools" samplerate:"44100" \
                          bitrate:"1379" duration:[0 TO 10]'
        parsed_filters = parse_query_filter_string(query_filter_str)
        filter_without_facet, has_facet_filter = remove_facet_filters(parsed_filters)
        self.assertTrue(has_facet_filter)
        self.assertEqual(filter_without_facet, 'duration:[0 TO 10]')

    def test_remove_facet_filters_special_char3(self):
        query_filter_str = 'grouping_pack:"..." tag:"da@," duration:[0 TO 1.1]'
        parsed_filters = parse_query_filter_string(query_filter_str)
        filter_without_facet, has_facet_filter = remove_facet_filters(parsed_filters)
        self.assertTrue(has_facet_filter)
        self.assertEqual(filter_without_facet, 'duration:[0 TO 1.1]')

    '''
    def test_search_prepare_parameters_non_ascii_query(self):
        # Simple test to check if some non ascii characters are correctly handled by search_prepare_parameters()
        request = self.factory.get(reverse('sounds-search')+'?q=Æ æ ¿ É')
        SessionMiddleware().process_request(request)
        AuthenticationMiddleware().process_request(request)
        request.session.save()
        query_params, advanced_search_params_dict, extra_vars = search_prepare_parameters(request)
        self.assertEqual(query_params['textual_query'], '\xc6 \xe6 \xbf \xc9')

    def test_split_filter_query_duration_and_facet(self):
        # We check that the combination of a duration filter and a facet filter (CC Attribution) works correctly.
        filter_query_string = 'duration:[0 TO 10] license:"attribution" username:"XavierFav" grouping_pack:"1_best-pack-ever"'
        parsed_filters = parse_query_filter_string(filter_query_string)
        filter_query_split = split_filter_query(filter_query_string, parsed_filters, '')

        # duraton filter is not a facet, but should stay present when removing a facet.
        expected_filter_query_split = [
            {'remove_url': 'duration:[0 TO 10]', 'name': 'license:"attribution"'}, 
        ]
        expected_filter_query_split = [
            {'remove_url': quote_plus('duration:[0 TO 10] username:"XavierFav" grouping_pack:"1_best-pack-ever"'), 'name': 'license:"attribution"'}, 
            {'remove_url': quote_plus('duration:[0 TO 10] license:"attribution" grouping_pack:"1_best-pack-ever"'), 'name': 'username:"XavierFav"'}, 
            {'remove_url': quote_plus('duration:[0 TO 10] license:"attribution" username:"XavierFav"'), 'name': 'pack:best-pack-ever'},
        ]

        # the order does not matter for the list of facet dicts.
        # we get the index of the correspondings facets dicts.
        filter_query_names = [filter_query_dict['name'] for filter_query_dict in filter_query_split]
        cc_attribution_facet_dict_idx = filter_query_names.index('license:"attribution"')
        username_facer_dict_idx = filter_query_names.index('username:"XavierFav"')
        grouping_pack_facet_dict_idx = filter_query_names.index('pack:best-pack-ever')

        # we use assertIn because the unicode strings that split_filter_query generates can incorporate 
        # additional spaces at the end of the string, which is not a problem.
        # Additonally, some additional spaces have been observed in the middle of the remove_url string. We replace double
        # spaces with single ones in this test. However, we should probably identify where does this additional spaces 
        # come from.
        # 1-Attribution
        self.assertIn(expected_filter_query_split[0]['name'],
                      filter_query_split[cc_attribution_facet_dict_idx]['name'])
        self.assertIn(expected_filter_query_split[0]['remove_url'],
                      filter_query_split[cc_attribution_facet_dict_idx]['remove_url'].replace('++', '+'))

        # 2-Username
        self.assertIn(expected_filter_query_split[1]['name'],
                      filter_query_split[username_facer_dict_idx]['name'])
        self.assertIn(expected_filter_query_split[1]['remove_url'],
                      filter_query_split[username_facer_dict_idx]['remove_url'].replace('++', '+'))

        # 3-Pack
        self.assertIn(expected_filter_query_split[2]['name'],
                      filter_query_split[grouping_pack_facet_dict_idx]['name'])
        self.assertIn(expected_filter_query_split[2]['remove_url'],
                      filter_query_split[grouping_pack_facet_dict_idx]['remove_url'].replace('++', '+'))

    def test_split_filter_query_special_chars(self):
        filter_query_string = 'license:"sampling+" grouping_pack:"1_example pack + @ #()*"'
        parsed_filters = parse_query_filter_string(filter_query_string)
        filter_query_split = split_filter_query(filter_query_string, parsed_filters, '')
        filter_query_names = [filter_query_dict['name'] for filter_query_dict in filter_query_split]

        expected_filter_query_split = [
            {'remove_url': quote_plus('grouping_pack:"1_example pack + @ #()*"'), 'name': 'license:"sampling+"'},
            {'remove_url': quote_plus('license:"sampling+"'), 'name': 'pack:example pack + @ #()*'},
        ]
        cc_samplingplus_facet_dict_idx = filter_query_names.index('license:"sampling+"')
        grouping_pack_facet_dict_idx = filter_query_names.index('pack:example pack + @ #()*')

        self.assertIn(expected_filter_query_split[0]['name'],
                      filter_query_split[cc_samplingplus_facet_dict_idx]['name'])
        self.assertIn(expected_filter_query_split[0]['remove_url'],
                      filter_query_split[cc_samplingplus_facet_dict_idx]['remove_url'])

        self.assertIn(expected_filter_query_split[1]['name'],
                      filter_query_split[grouping_pack_facet_dict_idx]['name'])
        self.assertIn(expected_filter_query_split[1]['remove_url'],
                      filter_query_split[grouping_pack_facet_dict_idx]['remove_url'])

    # most of these tests just ensure that no exception is returned when trying to parse filter strings 
    # that gave problems while developping the filter string parser function 
    # utils.search.lucene_parser.parse_query_filter_string()
    def test_parse_filter_query_special_created(self):
        filter_query_string = 'created:[NOW-7DAY TO NOW] license:"Creative Commons 0"'
        filter_query_split = parse_query_filter_string(filter_query_string)
        self.assertEqual(filter_query_split, [
            ['created', ':', '[', 'NOW-7DAY', ' TO ', 'NOW', ']'],
            ['license', ':', '"Creative Commons 0"'],
        ])

    def test_parse_filter_query_special_char(self):
        filter_query_string = 'grouping_pack:"32119_Conch Blowing (शङ्ख)"'
        filter_query_split = parse_query_filter_string(filter_query_string)
        self.assertEqual(filter_query_split, [
            ['grouping_pack', ':', '"32119_Conch Blowing (शङ्ख)"'],
        ])

    def test_parse_filter_query_special_char2(self):
        filter_query_string = 'grouping_pack:"2806_Hurt & Pain sounds"'
        filter_query_split = parse_query_filter_string(filter_query_string)
        self.assertEqual(filter_query_split, [
            ['grouping_pack', ':', '"2806_Hurt & Pain sounds"'],
        ])

    def test_parse_filter_query_geofilter(self):
        filter_query_string = 'tag:"cool" \'{!geofilt sfield=geotag pt=39.7750014,-94.2735586 d=50}\''
        filter_query_split = parse_query_filter_string(filter_query_string)
        self.assertEqual(filter_query_split, [
            ['tag', ':', '"cool"'],
            ["'{!", 'geofilt sfield=geotag pt=39.7750014,-94.2735586 d=50', "}'"]
        ])

    def test_parse_filter_composed_with_OR(self):
        filter_query_string = 'tag:"cool" license:("Attribution" OR "Creative Commons 0")'
        parsed_filters = parse_query_filter_string(filter_query_string)
        self.assertEqual(parsed_filters, [
            ['tag', ':', '"cool"'],
            ['license', ':', '(', '"Attribution"', "OR", '"Creative Commons 0"', ')']
        ])

    def test_parse_filter_nested_composed_with_OR(self):
        filter_query_string = '("Attribution" OR ("Attribution" OR "Creative Commons 0"))'
        parsed_filters = parse_query_filter_string(filter_query_string)

    @override_settings(ENABLE_SEARCH_RESULTS_CLUSTERING=True)
    def test_split_filter_query_cluster_facet(self):
        # We check that the combination of a duration filter, a facet filter (CC Attribution) and a cluster filter
        # works correctly.
        filter_query_string = 'duration:[0 TO 10] license:"attribution"'
        # the cluster filter is set in the second argument of split_filter_query()
        parsed_filters = parse_query_filter_string(filter_query_string)
        filter_query_split = split_filter_query(filter_query_string, parsed_filters, '1')

        expected_filter_query_split = [
            {'remove_url': quote_plus('duration:[0 TO 10]'), 'name': 'license:"attribution"'},
            {'remove_url': quote_plus('duration:[0 TO 10] license:"attribution"'), 'name': 'Cluster #1'}
        ]

        # check that the cluster facet exists
        filter_query_names = [filter_query_dict['name'] for filter_query_dict in filter_query_split]
        self.assertIn('Cluster #1', filter_query_names)

        # the order does not matter for the list of facet dicts.
        # we get the index of the correspondings facets dicts.
        cc_attribution_facet_dict_idx = filter_query_names.index('license:"attribution"')
        cluster_facet_dict_idx = filter_query_names.index('Cluster #1')

        self.assertIn(expected_filter_query_split[0]['name'],
                      filter_query_split[cc_attribution_facet_dict_idx]['name'])
        self.assertIn(expected_filter_query_split[0]['remove_url'],
                      filter_query_split[cc_attribution_facet_dict_idx]['remove_url'])

        self.assertIn(expected_filter_query_split[1]['name'],
                      filter_query_split[cluster_facet_dict_idx]['name'])
        self.assertIn(expected_filter_query_split[1]['remove_url'],
                      filter_query_split[cluster_facet_dict_idx]['remove_url'])
    '''
