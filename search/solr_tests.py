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

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from sounds.models import Sound
from utils.search.solr import Solr, SolrResponseInterpreter, SolrResponseInterpreterPaginator, SolrQuery
import mock
import copy


class SolarTests(TestCase):

    fixtures = ['users', 'sounds_with_tags']

    def search_prepare_query(self, search_query, filter_query, sort, current_page, sounds_per_page, field_list):
        id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id']
        tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag']
        description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description']
        username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username']
        pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
        original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename']
        field_weights = []
        field_weights.append(("id", id_weight))
        field_weights.append(("tag", tag_weight))
        field_weights.append(("description", description_weight))
        field_weights.append(("username", username_weight))
        field_weights.append(("pack_tokenized", pack_tokenized_weight))
        field_weights.append(("original_filename", original_filename_weight))
        start = (current_page - 1) * sounds_per_page

        query = SolrQuery()
        query.set_dismax_query(search_query, query_fields=field_weights,)
        query.set_query_options(start=start, rows=sounds_per_page, field_list=field_list, filter_query=filter_query, sort=sort)
        return query

    def test_dismax_search_response_ok(self):
        # Test queries to Solr with filters
        query = self.search_prepare_query("", "", None, 1, 10, None)
        solr = Solr(settings.SOLR_URL)

        response = solr.select(unicode(query))
        results = SolrResponseInterpreter(response)
        solr_ids = [element['id'] for element in results.docs]
        self.assertEqual(len(solr_ids), 10)

        query = self.search_prepare_query("sound", "tag:music", None, 1, 10, None)

        response = solr.select(unicode(query))
        results = SolrResponseInterpreter(response)
        solr_ids = [element['id'] for element in results.docs]

        for element in results.docs:
            self.assertTrue('music' in element['tag'] or 'Music' in element['tag'])
        self.assertEqual(len(solr_ids), 10)

        # Test that results match with both filters
        query = self.search_prepare_query("sound", "tag:music is_geotagged:true", None, 1, 10, None)
        response = solr.select(unicode(query))
        results = SolrResponseInterpreter(response)
        solr_ids = [element['id'] for element in results.docs]

        for element in results.docs:
            self.assertTrue('music' in element['tag'] or 'Music' in element['tag'])
            self.assertTrue(element['is_geotagged'])
        self.assertEqual(len(solr_ids), 10)

        # Test geotag filters are working

        filter_query = "is_geotagged:true {!geofilt sfield=geotag pt=41.3833,2.1833 d=10}"
        query = self.search_prepare_query("", filter_query, None, 1, 10, None)
        response = solr.select(unicode(query))
        results = SolrResponseInterpreter(response)
        solr_ids = [element['id'] for element in results.docs]

        for element in results.docs:
            lat, lng = element['geotag'][0].split(" ")
            self.assertTrue(float(lat)>-6 and float(lat)<5)
            self.assertTrue(float(lng)>35 and float(lng)<52)
            self.assertTrue(element['is_geotagged'])
        self.assertEqual(len(solr_ids), 10)


