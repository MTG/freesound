from unittest import mock

import pytest

from search.solrapi import SolrAPIError, SolrManagementAPI


def _mock_response(json_payload):
    resp = mock.Mock()
    resp.json.return_value = json_payload
    resp.raise_for_status = mock.Mock()
    return resp


@mock.patch("search.solrapi.requests")
def test_upsert_request_handler_adds_when_absent(mock_requests):
    # Successful add → 200 with no errorMessages.
    mock_requests.post.return_value = _mock_response({})

    api = SolrManagementAPI("http://search:8983", "freesound1234")
    api.upsert_request_handler("/select_similarity", "solr.SearchHandler")

    assert mock_requests.post.call_count == 1
    _, kwargs = mock_requests.post.call_args
    assert kwargs["json"] == {"add-requesthandler": {"name": "/select_similarity", "class": "solr.SearchHandler"}}


@mock.patch("search.solrapi.requests")
def test_upsert_request_handler_falls_back_to_update_on_duplicate(mock_requests):
    # Solr returns 200 with errorMessages when the handler already exists; we
    # then retry with update, which succeeds.
    mock_requests.post.side_effect = [
        _mock_response({"errorMessages": [{"add-requesthandler": "'/select_similarity' already exists"}]}),
        _mock_response({}),
    ]

    api = SolrManagementAPI("http://search:8983", "freesound1234")
    api.upsert_request_handler("/select_similarity", "solr.SearchHandler")

    assert mock_requests.post.call_count == 2
    second_call_json = mock_requests.post.call_args_list[1].kwargs["json"]
    assert second_call_json == {"update-requesthandler": {"name": "/select_similarity", "class": "solr.SearchHandler"}}


@mock.patch("search.solrapi.requests")
def test_upsert_request_handler_raises_when_update_also_fails(mock_requests):
    # Both add and update return errorMessages → surface as SolrAPIError.
    mock_requests.post.side_effect = [
        _mock_response({"errorMessages": [{"add-requesthandler": "boom"}]}),
        _mock_response({"errorMessages": [{"update-requesthandler": "boom too"}]}),
    ]

    api = SolrManagementAPI("http://search:8983", "freesound1234")
    with pytest.raises(SolrAPIError):
        api.upsert_request_handler("/select_similarity", "solr.SearchHandler")


@mock.patch("search.solrapi.requests")
def test_upsert_request_handler_includes_defaults(mock_requests):
    mock_requests.post.return_value = _mock_response({})

    api = SolrManagementAPI("http://search:8983", "freesound1234")
    api.upsert_request_handler("/select_similarity", "solr.SearchHandler", defaults={"defType": "dismax"})

    _, kwargs = mock_requests.post.call_args
    assert kwargs["json"]["add-requesthandler"]["defaults"] == {"defType": "dismax"}
