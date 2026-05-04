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

from django.core.paginator import InvalidPage, Paginator
from django.utils.functional import cached_property


class CountProvidedPaginator(Paginator):
    """A django Paginator that takes an optional object_count
    which is the length of object_list. This means that count() or
    len() doesn't have to be called"""

    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True, object_count=None):
        Paginator.__init__(self, object_list, per_page, orphans, allow_empty_first_page)

        self._count = object_count

    @cached_property
    def count(self):
        # If the count was provided return it, otherwise use the
        if self._count:
            return self._count
        return super().count


def paginate(request, qs, items_per_page=20, page_get_name="page", object_count=None):
    paginator = CountProvidedPaginator(qs, items_per_page, object_count=object_count)
    try:
        current_page = int(request.GET.get(page_get_name, 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        current_page = paginator.num_pages
        page = paginator.page(current_page)

    return dict(paginator=paginator, current_page=current_page, page=page)


def build_paginator_template_context(
    paginator,
    page,
    current_page,
    base_path,
    base_query,
    anchor="",
    non_grouped_number_of_results=-1,
    hx_target="",
):
    """Build context for ``templates/molecules/paginator.html``.

    ``base_path`` is the URL path that paginator links should point to (typically
    ``request.path``). ``base_query`` is a dict-like (e.g. ``QueryDict``) of
    query parameters to preserve across pages; ``page`` is always stripped and
    replaced with the target page number.
    """
    if paginator is None:
        return {}

    adjacent_pages = 3
    total_wanted = adjacent_pages * 2 + 1
    min_page_num = max(current_page - adjacent_pages, 1)
    max_page_num = min(current_page + adjacent_pages + 1, paginator.num_pages + 1)

    num_items = max_page_num - min_page_num

    if num_items < total_wanted and num_items < paginator.num_pages:
        if min_page_num == 1:
            max_page_num += min(total_wanted - num_items, paginator.num_pages - num_items)
        else:
            min_page_num -= min(total_wanted - num_items, paginator.num_pages - num_items)

    page_numbers = [n for n in range(min_page_num, max_page_num) if 0 < n <= paginator.num_pages]

    params = urllib.parse.urlencode(
        [
            (key.encode("utf-8"), value.encode("utf-8"))
            for (key, value) in base_query.items()
            if key.lower() != "page"
        ]
    )

    if params == "":
        url = base_path + "?page="
    else:
        url = base_path + "?" + params + "&page="

    if isinstance(page, dict):
        prev_page_num = page["previous_page_number"] if page.get("has_previous") else None
        next_page_num = page["next_page_number"] if page.get("has_next") else None
    else:
        prev_page_num = page.previous_page_number() if page.has_previous() else None
        next_page_num = page.next_page_number() if page.has_next() else None

    url_prev_page = url + str(prev_page_num) if prev_page_num is not None else None
    url_next_page = url + str(next_page_num) if next_page_num is not None else None
    url_first_page = url + "1"
    url_last_page = url + str(paginator.num_pages)

    if page_numbers:
        last_is_next = paginator.num_pages - 1 == page_numbers[-1]
    else:
        last_is_next = False

    return {
        "page": page,
        "paginator": paginator,
        "current_page": current_page,
        "page_numbers": page_numbers,
        "show_first": 1 not in page_numbers,
        "show_last": paginator.num_pages not in page_numbers,
        "last_is_next": last_is_next,
        "url": url,
        "url_prev_page": url_prev_page,
        "url_next_page": url_next_page,
        "url_first_page": url_first_page,
        "url_last_page": url_last_page,
        "prev_page_num": prev_page_num,
        "next_page_num": next_page_num,
        "last_page_num": paginator.num_pages,
        "anchor": anchor,
        "non_grouped_number_of_results": non_grouped_number_of_results,
        "hx_target": hx_target,
    }
