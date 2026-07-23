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
import pytest
from django.core.management import call_command
from django.core.paginator import Page, Paginator
from django.test import RequestFactory, TestCase
from django.urls import reverse

from general.templatetags.bw_templatetags import bw_paginator
from sounds.models import Sound
from utils.pagination import (
    CountProvidedPaginator,
    PreSlicedCountProvidedPaginator,
    build_paginator_template_context,
    paginate,
    read_page,
)


@pytest.fixture
def page_request():
    """Return a factory that builds a GET request with a given ``page`` param.

    Pass ``page=`` to set the page value, ``param=`` to change the query-param name,
    or any other keyword as an extra query param.
    """

    def _make(page=None, param="page", **extra):
        params = dict(extra)
        if page is not None:
            params[param] = page
        return RequestFactory().get("/", params)

    return _make


@pytest.fixture
def sounds(db):
    """Load the sound fixtures (14 sounds) and return them as a queryset."""
    call_command("loaddata", "licenses.json", "sounds.json")
    return Sound.objects.all()


def _paginator_context(page):
    return build_paginator_template_context(page, base_path="/search/", base_query={"q": "wind"})


class PaginatorTemplateContextTest(TestCase):
    def test_pagination_link_targets(self):
        page = Paginator(range(700 * 15), 15).page(5)
        ctx = _paginator_context(page)
        self.assertEqual(ctx["url_prev_page"], "/search/?q=wind&page=4")
        self.assertEqual(ctx["url_next_page"], "/search/?q=wind&page=6")
        self.assertEqual(ctx["url_last_page"], "/search/?q=wind&page=700")
        self.assertEqual(ctx["current_page"], 5)
        self.assertIs(ctx["paginator"], page.paginator)

    def test_none_page_returns_empty(self):
        self.assertEqual(build_paginator_template_context(None, base_path="/x/", base_query={}), {})


class PreSlicedCountProvidedPaginatorTest(TestCase):
    """object_list is a pre-sliced page: page() must not re-slice. Overflow page numbers
    clamp to the last page; a page number < 1 raises ValueError."""

    def _paginator(self, num_docs=15, num_found=100, num_per_page=15):
        docs = [{"id": i} for i in range(num_docs)]
        return PreSlicedCountProvidedPaginator(docs, num_per_page, num_found)

    def test_page_does_not_reslice(self):
        paginator = self._paginator(num_docs=15, num_found=100, num_per_page=15)
        # a normal paginator would return no items here (page 3 of 15 items per page
        # would be items [30:45] which don't exist).
        self.assertEqual(len(paginator.page(3).object_list), 15)

    def test_page_overflow_last_page(self):
        paginator = self._paginator(num_found=100, num_per_page=15)
        # getting page 50 clamps to page 7 ceil(100/15)
        self.assertEqual(paginator.num_pages, 7)
        self.assertEqual(paginator.page(50).number, 7)

        # getting the last page returns the last page
        self.assertEqual(paginator.page(7).number, 7)

    def test_page_underflow_raises(self):
        # Unlike overflow, page < 1 is a caller bug (callers clamp to >= 1 first), so we
        # raise rather than silently clamping.
        paginator = self._paginator()
        with self.assertRaises(ValueError):
            paginator.page(0)
        with self.assertRaises(ValueError):
            paginator.page(-3)

    def test_empty_results_have_one_page(self):
        paginator = PreSlicedCountProvidedPaginator([], 15, 0)
        self.assertEqual(paginator.num_pages, 1)
        self.assertEqual(list(paginator.page(1).object_list), [])

    def test_paginator_page(self):
        # a paginator with 5 objects and 2 per page is 3 pages
        paginator = PreSlicedCountProvidedPaginator([1, 2], 2, 5)
        page = paginator.page(2)
        self.assertIsInstance(page, Page)
        self.assertEqual(list(page.object_list), [1, 2])
        self.assertTrue(page.has_next())
        self.assertTrue(page.has_previous())
        self.assertTrue(page.has_other_pages())
        self.assertEqual(page.next_page_number(), 3)
        self.assertEqual(page.previous_page_number(), 1)

    def test_object_list_longer_than_per_page_raises(self):
        # it's an error to pass in 3 items with 2 declared per page.
        with self.assertRaises(ValueError):
            PreSlicedCountProvidedPaginator([1, 2, 3], 2, 5)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 1),  # no param
        ("abc", 1),  # non-numeric
        ("0", 1),  # zero, set to 1
        ("-5", 1),  # negative -> set to 1
        ("7", 7),  # normal value
    ],
    ids=["missing", "non-numeric", "zero", "negative", "in-range"],
)
def test_read_page_clamps_and_defaults(page_request, value, expected):
    assert read_page(page_request(page=value)) == expected


def test_read_page_custom_param_name(page_request):
    assert read_page(page_request(p="3"), param="p") == 3


def test_paginate_underflow_goes_to_first_page(page_request, sounds):
    """?page=0 must clamp to page 1, not snap to the last page."""
    result = paginate(page_request(page="0"), sounds, 10)
    assert result["page"].number == 1
    assert result["current_page"] == 1


def test_paginate_overflow_goes_to_last_page(page_request, sounds):
    """?page beyond the end clamps to the last page (14 sounds / 10 per page == 2 pages)."""
    result = paginate(page_request(page="999"), sounds, 10)
    assert result["page"].number == 2
    assert result["current_page"] == 2


def test_paginate_in_range_unchanged(page_request, sounds):
    result = paginate(page_request(page="2"), sounds, 10)
    assert result["page"].number == 2
    assert result["current_page"] == 2


class PaginationTest(TestCase):
    fixtures = ["licenses.json", "sounds.json"]

    def test_pagination_cache_count(self):
        """If you create a paginator, it'll call .count() once on the queryset
        to get the length, but not again when needing to use the number of items"""

        sounds = Sound.objects.all()

        with self.assertNumQueries(2):
            paginator = CountProvidedPaginator(sounds, 10)
            # Call count twice, should only run one query
            self.assertEqual(paginator.count, 14)
            self.assertEqual(paginator.count, 14)
            # and another query to evaluate the page. Call len() to force the qs to be evaluated
            first_page = paginator.page(1)
            self.assertEqual(len(first_page), 10)

    def test_pagination_provide_object_count(self):
        """If you pass a count into the paginator it won't call .count() on the queryset to
        get the count"""

        sounds = Sound.objects.all()

        with self.assertNumQueries(1):
            paginator = CountProvidedPaginator(sounds, 10, object_count=14)
            # Calls to .count will return the right value but won't cause a query to run
            self.assertEqual(paginator.count, 14)
            self.assertEqual(paginator.count, 14)
            # This should be the only query that runs, call len() to force the qs to be evaluated
            first_page = paginator.page(1)
            self.assertEqual(len(first_page), 10)

    def test_url_with_non_ascii_characters(self):
        """Paginator objects are passed a request object which includes a list of request GET parameters and values.
        The paginator uses this object to get parameters like the current page that is requested, and also to construct
        pagination links which contain all the same GET parameters as the initial request so that whatever things
        are determined there, will be preserved when moving to the next page. To do that the paginator iterates over
        all GET parameters and values. This test checks that if non-ascii characters are passed as GET parameter names
        or values, paginator does not break.
        """
        text_with_non_ascii = "�textèé"
        dummy_request = RequestFactory().get(
            reverse("sounds"),
            {
                text_with_non_ascii: "1",
                "param_name": text_with_non_ascii,
                "param2_name": "ok_value",
            },
        )
        paginator = paginate(dummy_request, Sound.objects.all(), 10)
        bw_paginator({}, paginator["page"], dummy_request)


def _capped_context(num_pages, current_page, max_pages=None):
    # a paginator_template_context that can adjust total number of pages and max allowed pages
    page = Paginator(range(num_pages * 15), 15).page(current_page)
    return build_paginator_template_context(page, base_path="/search/", base_query={"q": "wind"}, max_pages=max_pages)


def test_pagination_hides_prev_next_at_limits():
    assert _capped_context(num_pages=700, current_page=1)["url_prev_page"] is None
    assert _capped_context(num_pages=700, current_page=700)["url_next_page"] is None


def test_max_pages_caps_pagination():
    # search results with 700 pages but we limit to 100
    capped = _capped_context(num_pages=700, current_page=1, max_pages=100)
    assert capped["last_page_num"] == 100
    assert capped["url_last_page"] == "/search/?q=wind&page=100"

    # Normal prev/next below the cap...
    below = _capped_context(num_pages=700, current_page=50, max_pages=100)
    assert below["url_prev_page"] == "/search/?q=wind&page=49"
    assert below["url_next_page"] == "/search/?q=wind&page=51"

    # but no next link once we reach the capped last page.
    assert _capped_context(num_pages=700, current_page=100, max_pages=100)["url_next_page"] is None


def test_current_page_beyond_max_pages_raises():
    # Invalid situation (trying to paginate page 150 but we have a max of 100).
    with pytest.raises(ValueError):
        _capped_context(num_pages=700, current_page=150, max_pages=100)
