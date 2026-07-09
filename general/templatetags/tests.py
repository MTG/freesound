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

from django.core.paginator import Paginator
from django.template import Context, Template
from django.test import RequestFactory


def _render(num_pages, current_page, max_pages_expr):
    page = Paginator(range(num_pages * 15), 15).page(current_page)
    request = RequestFactory().get("/search/?q=wind")
    tpl = Template("{% load bw_templatetags %}{% bw_paginator page request anchor='sound' " + max_pages_expr + " %}")
    return tpl.render(Context({"page": page, "request": request}))


def test_pager_caps_last_page_link():
    # If the results page has 700 pages but we only want to show 100 then truncate the paginator
    # and don't show a link for 700
    html = _render(num_pages=700, current_page=1, max_pages_expr="max_pages=100")
    assert "page=100" in html
    assert "page=700" not in html


def test_pager_uncapped_when_no_max():
    html = _render(num_pages=700, current_page=1, max_pages_expr="")
    assert "page=700" in html


def test_next_arrow_hidden_at_capped_last_page():
    # On the capped last page the "next" arrow must not point past the cap.
    html = _render(num_pages=700, current_page=100, max_pages_expr="max_pages=100")
    assert 'title="Next Page"' not in html
    assert "page=101" not in html


def test_next_arrow_shown_below_cap():
    html = _render(num_pages=700, current_page=50, max_pages_expr="max_pages=100")
    assert 'title="Next Page"' in html
