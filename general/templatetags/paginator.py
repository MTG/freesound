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

import urllib
from django import template

register = template.Library()

@register.inclusion_tag('templatetags/paginator.html', takes_context=True)
def show_paginator(context, paginator, page, current_page, request, anchor="", non_grouped_number_of_results = -1 ):
    """
    Adds pagination context variables for use in displaying first, adjacent and
    last page links in addition to those created by the object_list generic
    view.
    """
 
    adjacent_pages = 3
    total_wanted = adjacent_pages * 2 + 1
    min_page_num = max(current_page - adjacent_pages, 1)
    max_page_num = min(current_page + adjacent_pages + 1, paginator.num_pages + 1)

    num_items = max_page_num - min_page_num

    if num_items < total_wanted and num_items < paginator.num_pages:
        if min_page_num == 1:
            # we're at the start, increment max_page_num
            max_page_num += min(total_wanted - num_items, paginator.num_pages - num_items)
        else:
            # we're at the end, decrement
            min_page_num -= min(total_wanted - num_items, paginator.num_pages - num_items)

    # although paginator objects are 0-based, we use 1-based paging
    page_numbers = [n for n in range(min_page_num, max_page_num) if n > 0 and n <= paginator.num_pages]

    params = urllib.urlencode([(key.encode('utf-8'), value.encode('utf-8')) for (key, value) in request.GET.items()
                               if key.lower() != u"page"])

    if params == "":
        url = request.path + u"?page="
    else:
        url = request.path + u"?" + params + u"&page="

    # The pagination could be over a queryset or over the result of a query to solr, so 'page' could be an object
    # if it's the case a query to the DB or a dict if it's the case of a query to solr
    if isinstance(page, dict):
        url_prev_page = url + str(page['previous_page_number'])
        url_next_page =  url + str(page['next_page_number'])
        url_first_page = url + '1'
    else:
        url_prev_page = None
        if page.has_previous():
             url_prev_page = url + str(page.previous_page_number())
        url_next_page = None
        if page.has_next():
             url_next_page = url + str(page.next_page_number())
        url_first_page = url + '1'
    url_last_page = url + str(paginator.num_pages)

    return {
        "page": page,
        "paginator": paginator,
        "current_page": current_page,
        "page_numbers": page_numbers,
        "show_first": 1 not in page_numbers,
        "show_last": paginator.num_pages not in page_numbers,
        "url" : url,
        "url_prev_page": url_prev_page,
        "url_next_page": url_next_page,
        "url_first_page": url_first_page,
        "url_last_page": url_last_page,
        "media_url": context['media_url'],
        "anchor": anchor,
        "non_grouped_number_of_results": non_grouped_number_of_results
    }
