from django.test import TestCase

from utils.search.backends import solr9pysolr

class SolrCommonTest(TestCase):
    def test_search_filter_make_intersection(self):

        filter_query = "username:alastairp"
        updated = solr9pysolr.Solr9PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "+username:alastairp")

        filter_query = "username:alastairp license:(a OR b)"
        updated = solr9pysolr.Solr9PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "+username:alastairp +license:(a OR b)")
