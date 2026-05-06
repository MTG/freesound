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

from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.test import TestCase

from utils.search.backends.solr9pysolr import Solr9PySolrSearchEngine
from utils.search.backends.solr555pysolr import (
    BOOLEAN_SHADOW_FIELDS,
    SEARCH_SOUNDS_BOOST_FUNCTIONS,
    get_solr_fieldname_from_freesound_fieldname,
)


def _empty_solr_response():
    return SimpleNamespace(
        docs=[],
        num_found=0,
        start=0,
        num_rows=0,
        non_grouped_number_of_results=0,
        facets={},
        highlighting={},
        q_time=0,
    )


def _expected_qf(field_weights, legacy):
    """Build the expected `qf` string from the same constants the implementation uses."""
    parts = []
    for field_name, weight in field_weights.items():
        solr_name = get_solr_fieldname_from_freesound_fieldname(field_name)
        if legacy and solr_name in BOOLEAN_SHADOW_FIELDS:
            solr_name = solr_name + "_bool"
        parts.append(f"{solr_name}^{weight}")
    return " ".join(parts)


class SearchSoundsRankingTest(TestCase):
    """Unit tests for the qf/bf params produced by Solr9PySolrSearchEngine.search_sounds.

    The behaviour we want to lock down:
        - default (use_legacy_search=False): qf uses canonical fields; bf carries
          rating + freshness boosts when sort is "Automatic by relevance".
        - legacy (use_legacy_search=True):  qf swaps in `_bool` shadow fields
          for every shadow-eligible solr field; bf is omitted.
        - boosts are skipped on explicit sorts even in default mode.
        - arbitrary fields the caller passes (e.g. via API v2 `weights`) follow
          the same shadow-suffix rule — verified for `comment`.
    """

    def _run_search(self, **search_kwargs):
        engine = Solr9PySolrSearchEngine()
        mock_index = mock.MagicMock()
        mock_index.search.return_value = _empty_solr_response()
        engine.sounds_index = mock_index
        engine.search_sounds(textual_query="foo", **search_kwargs)
        return mock_index.search.call_args.kwargs

    def test_legacy_mode_uses_bool_fields_and_no_bf(self):
        call_kwargs = self._run_search(use_legacy_search=True)

        expected_qf = _expected_qf(settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS, legacy=True)
        self.assertEqual(call_kwargs["qf"], expected_qf)
        # `id` is intentionally not in BOOLEAN_SHADOW_FIELDS (string field, no
        # similarity to swap) and should appear unsuffixed in the qf above.
        self.assertIn("id^4", call_kwargs["qf"])
        self.assertNotIn("id_bool", call_kwargs["qf"])
        self.assertNotIn("bf", call_kwargs)

    def test_default_mode_uses_canonical_fields_and_emits_bf(self):
        call_kwargs = self._run_search(use_legacy_search=False)

        expected_qf = _expected_qf(settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS, legacy=False)
        self.assertEqual(call_kwargs["qf"], expected_qf)
        self.assertNotIn("_bool", call_kwargs["qf"])
        self.assertEqual(call_kwargs["bf"], list(SEARCH_SOUNDS_BOOST_FUNCTIONS))

    def test_boosts_skipped_for_explicit_sort(self):
        call_kwargs = self._run_search(
            use_legacy_search=False,
            sort=settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,
        )
        self.assertNotIn("bf", call_kwargs)

    def test_arbitrary_field_is_shadowed_in_legacy_mode(self):
        # comment is not in SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS but is text-typed
        # and reachable via apiv2_utils.parse_weights_parameter — its shadow must work.
        call_kwargs = self._run_search(
            use_legacy_search=True,
            query_fields={"comment": 1, "tags": 4},
        )
        self.assertIn("comment_bool^1", call_kwargs["qf"])
        self.assertIn("tag_bool^4", call_kwargs["qf"])

    def test_constants_align(self):
        # Catch drift if someone adds a shadow to SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS
        # without updating BOOLEAN_SHADOW_FIELDS — the test_legacy_mode... test would
        # still pass because both sides derive from BOOLEAN_SHADOW_FIELDS, so we
        # additionally assert the expected solr field names are what we think they are.
        weights = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS
        solr_names = {get_solr_fieldname_from_freesound_fieldname(f) for f in weights}
        # All the text-typed fields in defaults should have a shadow defined
        self.assertEqual(solr_names & BOOLEAN_SHADOW_FIELDS, {"tag", "description", "username", "pack", "name"})
        # `id` is in defaults and is not (and should not be) a shadow
        self.assertIn("id", solr_names)
        self.assertNotIn("id", BOOLEAN_SHADOW_FIELDS)

    def test_module_level_boost_functions_are_immutable(self):
        # Tuple, not list — defensive against accidental module-level mutation.
        self.assertIsInstance(SEARCH_SOUNDS_BOOST_FUNCTIONS, tuple)
        self.assertIsInstance(BOOLEAN_SHADOW_FIELDS, frozenset)

    def test_boost_functions_reference_expected_fields(self):
        # If anyone retunes the boosts, this catches removal of the safety
        # invariants documented next to SEARCH_SOUNDS_BOOST_FUNCTIONS:
        # - rating boost must be gated on num_ratings to avoid scoring an
        #   already-zero avg_rating
        # - freshness boost must reference `created`, the only created-time field.
        joined = " ".join(SEARCH_SOUNDS_BOOST_FUNCTIONS)
        self.assertIn("num_ratings", joined)
        self.assertIn("avg_rating", joined)
        self.assertIn("created", joined)


class SearchSoundsRankingMockingHelperTest(TestCase):
    """Sanity checks on the test helper itself, since the assertions above
    depend on it being correct."""

    def test_expected_qf_default_mode(self):
        expected = _expected_qf(
            {settings.SEARCH_SOUNDS_FIELD_TAGS: 4, settings.SEARCH_SOUNDS_FIELD_NAME: 2},
            legacy=False,
        )
        self.assertEqual(expected, "tag^4 name^2")

    def test_expected_qf_legacy_mode(self):
        expected = _expected_qf(
            {settings.SEARCH_SOUNDS_FIELD_TAGS: 4, settings.SEARCH_SOUNDS_FIELD_ID: 4},
            legacy=True,
        )
        # tag is a shadow, id is not
        self.assertEqual(expected, "tag_bool^4 id^4")
