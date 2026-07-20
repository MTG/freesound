import http.client

import pysolr
import pytest
import requests
from django.test import TestCase

from utils.search import (
    SearchEngineBadRequestException,
    SearchEngineException,
    SearchEngineInternalErrorException,
    SearchEngineInvalidValueException,
    SearchEngineSyntaxErrorException,
    SearchEngineTimeoutException,
    SearchEngineUnavailableException,
    SearchEngineUndefinedFieldException,
)
from utils.search.backends import solr555pysolr
from utils.search.backends.solr555pysolr import _raise_search_engine_exception


class Solr555PySolrTest(TestCase):
    def test_search_filter_make_intersection(self):
        filter_query = "username:alastairp"
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "+username:alastairp")

        filter_query = "username:alastairp license:(a OR b)"
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "+username:alastairp +license:(a OR b)")

        filter_query = "-username:alastairp"
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "-username:alastairp")

        filter_query = "username:alastairp -license:(a OR b)"
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, "+username:alastairp -license:(a OR b)")


def _solr_error(message, cause=None):
    """Build a pysolr.SolrError the way pysolr raises it: a message string, optionally
    chained from an underlying exception (as `raise SolrError(...) from err` would set)."""
    error = pysolr.SolrError(message)
    error.__cause__ = cause
    return error


class TestRaiseSearchEngineException:
    """_raise_search_engine_exception classifies pysolr's opaque SolrError into a typed
    exception, so each error family becomes a distinct Sentry issue."""

    def test_client_timeout_from_chained_cause(self):
        # pysolr chains the original requests timeout via `raise SolrError(...) from err`
        error = _solr_error("Connection to server timed out", cause=requests.exceptions.ReadTimeout())
        with pytest.raises(SearchEngineTimeoutException):
            _raise_search_engine_exception(error)

    def test_solr_side_timeout_is_not_a_timeout_exception(self):
        # A Solr-internal timeout arrives as an HTTP response with no chained cause. We
        # deliberately no longer string-match "timed out": it surfaces as a generic 5xx.
        error = _solr_error("Solr responded with an error (HTTP 500): [Reason: search timed out]")
        with pytest.raises(SearchEngineInternalErrorException):
            _raise_search_engine_exception(error)

    def test_undefined_field(self):
        error = _solr_error("Solr responded with an error (HTTP 400): [Reason: undefined field foobar]")
        with pytest.raises(SearchEngineUndefinedFieldException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineUndefinedFieldException

    def test_syntax_error_cannot_parse(self):
        error = _solr_error("Solr responded with an error (HTTP 400): [Reason: Cannot parse 'foo:': ...]")
        with pytest.raises(SearchEngineSyntaxErrorException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineSyntaxErrorException

    def test_syntax_error_named_syntaxerror(self):
        error = _solr_error(
            "Solr responded with an error (HTTP 400): [Reason: org.apache.solr.search.SyntaxError: ...]"
        )
        with pytest.raises(SearchEngineSyntaxErrorException):
            _raise_search_engine_exception(error)

    def test_invalid_value(self):
        error = _solr_error(
            "Solr responded with an error (HTTP 400): [Reason: Invalid Number: 5,052 for field duration]"
        )
        with pytest.raises(SearchEngineInvalidValueException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineInvalidValueException

    def test_unclassified_4xx_is_bad_request(self):
        error = _solr_error("Solr responded with an error (HTTP 400): [Reason: something we don't recognise]")
        with pytest.raises(SearchEngineBadRequestException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineBadRequestException

    def test_unclassified_5xx_is_internal_error(self):
        error = _solr_error("Solr responded with an error (HTTP 503): [Reason: Parent query must not match any docs]")
        with pytest.raises(SearchEngineInternalErrorException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineInternalErrorException

    def test_connection_error_is_unavailable(self):
        # No HTTP status (Solr never answered); pysolr chains the connection failure.
        error = _solr_error(
            "Failed to connect to server at 'http://solr:8983/...'",
            cause=requests.exceptions.ConnectionError(),
        )
        with pytest.raises(SearchEngineUnavailableException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineUnavailableException

    def test_httpexception_is_unavailable(self):
        # pysolr also chains http.client.HTTPException for broken HTTP responses.
        error = _solr_error("Broken response from server", cause=http.client.HTTPException())
        with pytest.raises(SearchEngineUnavailableException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineUnavailableException

    def test_invalid_value_wrapped_in_cannot_parse(self):
        # Solr prepends "Cannot parse '…':" to the specific invalid-number reason; the specific
        # family must win over the generic "cannot parse" (syntax) branch.
        error = _solr_error(
            "Solr responded with an error (HTTP 400): [Reason: Cannot parse 'duration:[5,052 TO *]': "
            "Invalid Number: 5,052]"
        )
        with pytest.raises(SearchEngineInvalidValueException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineInvalidValueException

    def test_undefined_field_wrapped_in_cannot_parse(self):
        error = _solr_error(
            "Solr responded with an error (HTTP 400): [Reason: Cannot parse 'foobar:x': undefined field foobar]"
        )
        with pytest.raises(SearchEngineUndefinedFieldException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineUndefinedFieldException

    def test_unparseable_message_falls_back_to_base(self):
        error = _solr_error("something went wrong with no HTTP code")
        with pytest.raises(SearchEngineException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineException
