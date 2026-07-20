import http.client
from unittest import mock

import pysolr
import pytest
import requests
from django.test import TestCase

from utils.search import (
    SearchEngineBadRequestException,
    SearchEngineException,
    SearchEngineInternalErrorException,
    SearchEngineInvalidValueException,
    SearchEngineTimeoutException,
    SearchEngineUnavailableException,
    SearchEngineUndefinedFieldException,
)
from utils.search.backends import solr9pysolr, solr555pysolr
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

        filter_query = 'username:alastairp -license:(a OR b) collection:"my super: collection"'
        updated = solr555pysolr.Solr555PySolrSearchEngine().search_filter_make_intersection(filter_query)
        self.assertEqual(updated, '+username:alastairp -license:(a OR b) +collection:"my super: collection"')


class TestTransportErrors:
    # If pysolr raises an error with an underlying cause, classify it properly
    @mock.patch("pysolr.Solr.get_session")
    def test_client_timeout_from_chained_cause(self, get_session):
        get_session.return_value.get.side_effect = requests.exceptions.ReadTimeout()
        with pytest.raises(SearchEngineTimeoutException):
            solr9pysolr.Solr9PySolrSearchEngine().search_sounds()

    @mock.patch("pysolr.Solr.get_session")
    def test_connection_error_is_unavailable(self, get_session):
        get_session.return_value.get.side_effect = requests.exceptions.ConnectionError()
        with pytest.raises(SearchEngineUnavailableException):
            solr9pysolr.Solr9PySolrSearchEngine().search_sounds()

    @mock.patch("pysolr.Solr.get_session")
    def test_httpexception_is_unavailable(self, get_session):
        get_session.return_value.get.side_effect = http.client.HTTPException()
        with pytest.raises(SearchEngineUnavailableException):
            solr9pysolr.Solr9PySolrSearchEngine().search_sounds()


class TestErrorMessageClassification:
    # Solr returns a text message based on an error from solr, we categorise it correctly
    def test_solr_side_timeout_is_not_a_timeout_exception(self):
        # An HTTP 500 mentioning a timeout is still a server error.
        error = pysolr.SolrError("Solr responded with an error (HTTP 500): [Reason: search timed out]")
        with pytest.raises(SearchEngineInternalErrorException):
            _raise_search_engine_exception(error)

    def test_unclassified_4xx_is_bad_request(self):
        error = pysolr.SolrError("Solr responded with an error (HTTP 400): [Reason: something we don't recognise]")
        with pytest.raises(SearchEngineBadRequestException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineBadRequestException

    def test_unclassified_5xx_is_internal_error(self):
        error = pysolr.SolrError(
            "Solr responded with an error (HTTP 503): [Reason: Parent query must not match any docs]"
        )
        with pytest.raises(SearchEngineInternalErrorException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineInternalErrorException

    def test_invalid_value_wrapped_in_cannot_parse(self):
        # Solr prepends "Cannot parse ...:" to lots of different errors. Make sure that we
        # catch the specific message instead of the generic one
        error = pysolr.SolrError(
            "Solr responded with an error (HTTP 400): [Reason: Cannot parse 'duration:[5,052 TO *]': "
            "Invalid Number: 5,052]"
        )
        with pytest.raises(SearchEngineInvalidValueException):
            _raise_search_engine_exception(error)

    def test_undefined_field_wrapped_in_cannot_parse(self):
        error = pysolr.SolrError(
            "Solr responded with an error (HTTP 400): [Reason: Cannot parse 'foobar:x': undefined field foobar]"
        )
        with pytest.raises(SearchEngineUndefinedFieldException):
            _raise_search_engine_exception(error)

    def test_unparseable_message_falls_back_to_base(self):
        error = pysolr.SolrError("something went wrong with no HTTP code")
        with pytest.raises(SearchEngineException) as excinfo:
            _raise_search_engine_exception(error)
        assert excinfo.type is SearchEngineException
