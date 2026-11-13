import pytest
from django.test import TestCase

from utils.search.backends import solr555pysolr
from utils.search.backends.solr_common import sanitize_dismax_query

# (input, expected) for the dismax query sanitizer. Balanced/normal queries pass through untouched;
# unbalanced quotes and leading/trailing dangling operators (which make the Solr parser 400) are
# trimmed. A fully-stripped query becomes empty and degrades to match-all via q.alt.
SANITIZE_CASES = [
    ("drum loop", "drum loop"),
    ('"drum loop"', '"drum loop"'),
    ("C++", "C++"),
    ("+drum -bass", "+drum -bass"),
    ("don't stop", "don't stop"),
    ("", ""),
    ('"drum', "drum"),
    ("drum OR", "drum"),
    ("OR drum", "drum"),
    ("AND", ""),
    ("foo +", "foo"),
    ("foo \\", "foo"),
    ('" OR "1"="1" --', "1=1"),
]


@pytest.mark.parametrize("query, expected", SANITIZE_CASES)
def test_sanitize_dismax_query(query, expected):
    assert sanitize_dismax_query(query) == expected


class SolrCommonTest(TestCase):
    def test_search_filter_make_intersection(self):
        filter_query = "username:alastairp"
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "+username:alastairp")

        filter_query = "username:alastairp license:(a OR b)"
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "+username:alastairp +license:(a OR b)")

        filter_query = 'username:alastairp -license:(a OR b) collection:"my super: collection"'
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, '+username:alastairp -license:(a OR b) +collection:"my super: collection"')
