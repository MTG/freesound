import pytest
from django.conf import settings

from utils.search import SearchEngineException
from utils.search.backends.solr555pysolr import Solr555PySolrSearchEngine
from utils.search.backends.solr_common import SolrQuery


def test_search_process_sort_default():
    sort = Solr555PySolrSearchEngine().search_process_sort(settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC)
    assert sort == ["score desc"]


def test_search_process_sort_rating_highest_adds_num_ratings():
    sort = Solr555PySolrSearchEngine().search_process_sort(settings.SEARCH_SOUNDS_SORT_OPTION_RATING_HIGHEST_FIRST)
    assert sort == ["avg_rating desc", "num_ratings desc"]


def test_search_process_sort_rating_lowest_adds_num_ratings():
    sort = Solr555PySolrSearchEngine().search_process_sort(settings.SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST)
    assert sort == ["avg_rating asc", "num_ratings desc"]


def test_set_query_options_sort_none():
    query = SolrQuery()
    query.set_query_options(field_list=["id"])
    assert query.params["sort"] is None
    assert query.params["fl"] == "id"


def test_set_query_options_sort_explicit_none():
    query = SolrQuery()
    query.set_query_options(sort=None, field_list=["id"])
    assert query.params["sort"] is None
    assert query.params["fl"] == "id"


def test_set_query_options_sort_dist_adds_field():
    query = SolrQuery()
    sort, dist_field = Solr555PySolrSearchEngine().search_process_sort_distance("bpm:0.5")
    assert sort == ["dist(2,bpm_d,0.5) asc"]
    assert dist_field == "dist:dist(2,bpm_d,0.5)"
    query.set_query_options(sort=sort, field_list=["id", dist_field])
    assert query.params["sort"] == ",".join(sort)
    assert query.params["fl"] == "id,dist:dist(2,bpm_d,0.5)"


def test_set_query_options_sort_dist_without_ordering():
    query = SolrQuery()
    sort = ["dist(2,foo,1.0)"]
    dist_field = "dist:dist(2,foo,1.0)"
    query.set_query_options(sort=sort, field_list=["id", dist_field])
    assert query.params["sort"] == "dist(2,foo,1.0)"
    assert query.params["fl"] == "id,dist:dist(2,foo,1.0)"


def test_set_query_options_sort_type_error():
    # If sort is not a list, raise a ValueError
    query = SolrQuery()
    with pytest.raises(ValueError):
        query.set_query_options(sort="dist(2,foo,1.0) asc", field_list=["id"])


def test_set_query_options_sort_score_desc_for_similarity():
    # Similarity search always uses score desc and should not append extra fields.
    query = SolrQuery()
    query.set_query_options(sort=["score desc"], field_list=["id"])
    assert query.params["sort"] == "score desc"
    assert query.params["fl"] == "id"


def test_search_process_sort_distance_multiple_fields():
    sort, dist_field = Solr555PySolrSearchEngine().search_process_sort_distance("bpm:0.5,beat_count:2")
    assert sort == ["dist(2,bpm_d,beat_count_i,0.5,2.0) asc"]
    assert dist_field == "dist:dist(2,bpm_d,beat_count_i,0.5,2.0)"


def test_search_process_sort_distance_invalid_target():
    with pytest.raises(SearchEngineException):
        Solr555PySolrSearchEngine().search_process_sort_distance("bpm:not-a-number")
