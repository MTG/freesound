import urllib.parse

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from utils.search import SearchEngineException
from utils.search.filter_validation import find_dropped_filters, parse_filter, validate_filter_types
from utils.search.search_query_processor import SearchQueryProcessor


def _decode_f_from_url(path: str) -> str:
    """Same as in SearchQueryProcessor.__init__"""
    request = RequestFactory().get(path)
    return urllib.parse.unquote(request.GET.get("f", "")).strip()


def _build_sqp(url):
    request = RequestFactory().get(url)
    request.user = AnonymousUser()
    return SearchQueryProcessor(request)


TYPE_CORRUPTION_URLS = [
    pytest.param(
        # filter decodes to bitdepth:16+bitrate:1379, which parses
        # to bitdepth value '16+bitrate:1379', and is rejected by solr
        "/browse/tags/?f=bitdepth%3A16%2Bbitrate%3A1379",
        "bitdepth",
        id="bitdepth+bitrate",
    ),
    pytest.param(
        # filter decodes to samplerate:22050+tag:"simmons", which parses
        # to samplerate value '22050+tag:"simmons"', and is rejected by solr
        "/search/?f=samplerate%3A22050%2Btag%3A%22simmons%22",
        "samplerate",
        id="synthetic_original-sentry-shape",
    ),
]


@pytest.mark.parametrize("url_path, field", TYPE_CORRUPTION_URLS)
def test_url_type_corruption_detected(url_path, field):
    # badly encoded + makes the value of a field invalid
    nodes = parse_filter(_decode_f_from_url(url_path))
    verdict = validate_filter_types(nodes)
    assert verdict is not None and field in verdict
    assert find_dropped_filters(nodes) == []


DROPPED_FILTER_URLS = [
    pytest.param(
        # Decodes to tag:"tap"+username:"ascap" - tag:tap and username:ascap
        # with a + before it - turns into 'MUST username:ascap' rather than a space
        # Our query parser ignores `Plus` fields, so it is reported as a dropped field
        "/browse/tags/?f=tag%3A%22tap%22%2Busername%3A%22ascap%22",
        ['username:"ascap"'],
        [("tag", '"tap"')],
        id="tag+username",
    ),
    pytest.param(
        # Decodes to tag:"lounge"+samplerate:8000. Same as above, samplerate is validated
        # as a valid int, but is still dropped because it's a `Plus` field
        "/browse/tags/?f=tag%3A%22lounge%22%2Bsamplerate%3A8000",
        ["samplerate:8000"],
        [("tag", '"lounge"')],
        id="tag+samplerate-unquoted",
    ),
    pytest.param(
        # Multiple %2B decodes to +, all filters after the first one are dropped
        "/browse/tags/?f=tag%3A%22electronic%22%2Btag%3A%22synth%22%2Btag%3A%22beat%22",
        ['tag:"synth"', 'tag:"beat"'],
        [("tag", '"electronic"')],
        id="tag+tag+tag",
    ),
    pytest.param(
        # Mixed encoding: samplerate:"192000" is quoted but is still a valid int
        # after removing "" so is kept
        "/browse/tags/?f=tag%3A%22Blood%22%2Btag%3A%22heart-beat%22+samplerate%3A%22192000%22",
        ['tag:"heart-beat"'],
        [("tag", '"Blood"'), ("samplerate", '"192000"')],
        id="quoted-samplerate-not-flagged",
    ),
]


@pytest.mark.parametrize("url_path, dropped, kept", DROPPED_FILTER_URLS)
def test_url_dropped_filters_reported(url_path, dropped, kept):
    # These URLs all have valid types for filter values, but SearchQueryProcessor drops
    # Plus-wrapped filters without telling the user. The remaining filters
    # are used for the search query.
    nodes = parse_filter(_decode_f_from_url(url_path))
    assert validate_filter_types(nodes) is None
    assert find_dropped_filters(nodes) == dropped
    assert _build_sqp(url_path).non_option_filters == kept


def test_url_legitimate_plus_not_flagged():
    # literal `+` between filters (decodes to space) and valid `+` inside a
    # Phrase ("Sampling+" is a real CC license): both accepted.
    nodes = parse_filter(_decode_f_from_url("/search/?f=tag%3A%22ducks%22+license%3A%22Sampling%2B%22"))
    assert validate_filter_types(nodes) is None
    assert find_dropped_filters(nodes) == []


def test_sqp_rejects_invalid_filter():
    # Check that SearchQueryProcessor sets self.errors if a field is invalid
    sqp = _build_sqp("/search/?f=samplerate%3Aabc")
    assert "samplerate" in sqp.errors


def test_sqp_with_errors_refuses_to_build_query_params():
    # a SQP with errors must never produce query params for the search engine.
    sqp = _build_sqp("/search/?f=samplerate%3Aabc")
    assert sqp.errors
    with pytest.raises(SearchEngineException):
        sqp.as_query_params()


SQP_ACCEPT_CASES = [
    pytest.param("/search/?f=samplerate%3A44100", id="bare-typed-int"),
    pytest.param("/search/?f=tag%3A%22reverb%22", id="bare-tag-phrase"),
    pytest.param("/search/?f=duration%3A%5B0+TO+10%5D", id="range-expr"),
    pytest.param("/search/?f=tag%3A%22ducks%22+license%3A%22Sampling%2B%22", id="legit-plus-in-phrase"),
    pytest.param(
        "/browse/tags/?f=tag%3A%22Blood%22%2Btag%3A%22heart-beat%22+samplerate%3A%22192000%22",
        id="quoted-samplerate-not-false-positive",
    ),
    pytest.param("/search/?f=", id="empty-f"),
    pytest.param("/search/?q=drum", id="no-f-param"),
]


@pytest.mark.parametrize("url", SQP_ACCEPT_CASES)
def test_sqp_accepts_valid(url):
    sqp = _build_sqp(url)
    assert not sqp.errors, f"Expected no errors for {url!r}, got {sqp.errors!r}"


VALID_FILTERS = [
    pytest.param("samplerate:44100", id="bare-int-typed"),
    pytest.param('bitdepth:16 tag:"reverb" channels:1', id="multi-filter-all-valid"),
    pytest.param("duration:[0 TO 10]", id="range-expr-skipped"),
    pytest.param("samplerate:[* TO 48000]", id="open-range-expr-skipped"),
    pytest.param("samplerate:>=44100", id="from-expr-skipped"),
    pytest.param("samplerate:(44100 OR 48000)", id="fieldgroup-expr-skipped"),
    pytest.param("samplerate:44100^2", id="boost-expr-skipped"),
    pytest.param('tag:"reverb"', id="non-typed-field-ignored"),
    pytest.param('tagfacet:"can"', id="legacy-tagfacet-ignored"),
    pytest.param('license:"Sampling+"', id="plus-inside-phrase-tolerated"),
    pytest.param('samplerate:"192000"', id="quoted-int-on-pint-field"),
    pytest.param("samplerate:*", id="wildcard-exists-query-tolerated"),
    pytest.param("", id="empty-string"),
]


@pytest.mark.parametrize("filter_string", VALID_FILTERS)
def test_valid_filters_accepted(filter_string):
    nodes = parse_filter(filter_string)
    assert validate_filter_types(nodes) is None
    assert find_dropped_filters(nodes) == []


INVALID_FILTERS = [
    pytest.param("samplerate:abc", "samplerate", id="non-numeric-samplerate"),
    pytest.param("channels:stereo", "channels", id="non-numeric-channels"),
    pytest.param("bitdepth:twentyfour", "bitdepth", id="non-numeric-bitdepth"),
    pytest.param("bitdepth:16+bitrate:1379", "bitdepth", id="type-corruption-bare-string"),
    pytest.param('samplerate:22050+tag:"simmons"', "samplerate", id="original-sentry-bare-string"),
]


@pytest.mark.parametrize("filter_string, must_mention", INVALID_FILTERS)
def test_invalid_filters_rejected(filter_string, must_mention):
    verdict = validate_filter_types(parse_filter(filter_string))
    assert verdict is not None, f"Expected error for {filter_string!r}"
    assert must_mention in verdict, f"Expected {must_mention!r} in verdict, got {verdict!r}"
