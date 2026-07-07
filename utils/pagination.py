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

import urllib.parse

from django.core.paginator import Page, Paginator
from django.http import HttpRequest
from django.utils.functional import cached_property


class CountProvidedPaginator(Paginator):
    """A django Paginator that takes an optional object_count
    which is the length of object_list. This means that count() or
    len() doesn't have to be called"""

    def __init__(
        self,
        object_list,
        per_page: int,
        orphans: int = 0,
        allow_empty_first_page: bool = True,
        object_count: int | None = None,
    ) -> None:
        Paginator.__init__(self, object_list, per_page, orphans, allow_empty_first_page)

        self._count = object_count

    @cached_property
    def count(self) -> int:
        # If the count was provided return it, otherwise use the
        if self._count:
            return self._count
        return super().count


class PreSlicedCountProvidedPaginator(CountProvidedPaginator):
    """A CountProvidedPaginator whose ``object_list`` is already sliced to the specific page
    (e.g. by solr)."""

    def __init__(self, object_list: list, per_page: int, object_count: int) -> None:
        """
        Args:
            object_list: the results for a single, already-sliced page.
            per_page: number of results per page.
            object_count: total number of results across all pages.
        """
        if len(object_list) > per_page:
            # Because object_list is pre-sliced it must contain as many items
            # as are claimed in per_page (or fewer if it's the last page)
            raise ValueError(f"object_list size must be less than or equal to {per_page=} ")
        super().__init__(object_list, per_page, object_count=object_count)

    def page(self, number: int | str) -> Page:
        """Return the ``Page`` for ``number``.

        Because the object list is already sliced, the `number` argument is only used for
        validation (it must be within `object_count/per_page` and >=1)
        and is used verbatim in the returned Page object.
        """
        number = int(number)
        if number < 1:
            raise ValueError(f"page number must be >= 1, got {number}")
        number = min(number, self.num_pages)
        return self._get_page(self.object_list, number, self)


def read_page(request: HttpRequest, param: str = "page") -> int:
    """Read the requested page number from the request.

    If the page number is not set or not a number, return 1
    Return page 1 for any number < 1
    """
    try:
        page = int(request.GET.get(param, 1))
    except ValueError:
        return 1
    return max(page, 1)


def paginate(
    request: HttpRequest,
    qs,
    items_per_page: int = 20,
    page_get_name: str = "page",
    object_count: int | None = None,
) -> dict:
    paginator = CountProvidedPaginator(qs, items_per_page, object_count=object_count)
    page_param = read_page(request, page_get_name)
    # If the requested page is greater than the number of pages in the queryset,
    # clamp it to the max valid value
    current_page = min(page_param, paginator.num_pages)
    page = paginator.page(current_page)
    return dict(paginator=paginator, current_page=current_page, page=page)


def build_paginator_template_context(
    page: Page | None,
    base_path: str,
    base_query,
    anchor: str = "",
    non_grouped_number_of_results: int = -1,
    hx_target: str = "",
    max_pages: int | None = None,
) -> dict:
    """Build context for ``templates/molecules/paginator.html``.

    ``page``'s ``paginator`` and ``number`` are derived here.
    ``base_path`` is the URL path that paginator links should point to (typically
    ``request.path``). ``base_query`` is a dict-like (e.g. ``QueryDict``) of
    query parameters to preserve across pages; ``page`` is always stripped and
    replaced with the target page number.
    ``max_pages``: If set then don't show pages past this value even if there are more.
    """
    if page is None:
        return {}

    paginator = page.paginator
    current_page = page.number

    last_page_number = paginator.num_pages
    if max_pages is not None:
        last_page_number = min(last_page_number, max_pages)
        if current_page > last_page_number:
            # The pager can't render a page past its max allowed value
            raise ValueError(f"current_page ({current_page}) is beyond max_pages ({max_pages})")

    adjacent_pages = 3
    total_wanted = adjacent_pages * 2 + 1
    min_page_num = max(current_page - adjacent_pages, 1)
    max_page_num = min(current_page + adjacent_pages + 1, last_page_number + 1)

    num_items = max_page_num - min_page_num

    if num_items < total_wanted and num_items < last_page_number:
        if min_page_num == 1:
            max_page_num += min(total_wanted - num_items, last_page_number - num_items)
        else:
            min_page_num -= min(total_wanted - num_items, last_page_number - num_items)

    page_numbers = [n for n in range(min_page_num, max_page_num) if 0 < n <= last_page_number]

    params = urllib.parse.urlencode(
        [(key.encode("utf-8"), value.encode("utf-8")) for (key, value) in base_query.items() if key.lower() != "page"]
    )

    if params == "":
        url = base_path + "?page="
    else:
        url = base_path + "?" + params + "&page="

    prev_page_num = page.previous_page_number() if page.has_previous() else None
    next_page_num = page.next_page_number() if page.has_next() else None

    # Don't show a "next" link past the last navigable page
    # (e.g. if we're on page 120 of 130 but the settings max is 100).
    if next_page_num is not None and current_page >= last_page_number:
        next_page_num = None

    url_prev_page = url + str(prev_page_num) if prev_page_num is not None else None
    url_next_page = url + str(next_page_num) if next_page_num is not None else None
    url_first_page = url + "1"
    url_last_page = url + str(last_page_number)

    if page_numbers:
        last_is_next = last_page_number - 1 == page_numbers[-1]
    else:
        last_is_next = False

    return {
        "page": page,
        "paginator": paginator,
        "current_page": current_page,
        "page_numbers": page_numbers,
        "show_first": 1 not in page_numbers,
        "show_last": last_page_number not in page_numbers,
        "last_is_next": last_is_next,
        "url": url,
        "url_prev_page": url_prev_page,
        "url_next_page": url_next_page,
        "url_first_page": url_first_page,
        "url_last_page": url_last_page,
        "prev_page_num": prev_page_num,
        "next_page_num": next_page_num,
        "last_page_num": last_page_number,
        "anchor": anchor,
        "non_grouped_number_of_results": non_grouped_number_of_results,
        "hx_target": hx_target,
    }
