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

from search.abuse import is_over_hard_page_limit


def test_is_over_hard_page_limit(settings):
    settings.SEARCH_MAX_PAGE_HARD_LIMIT = 100
    assert is_over_hard_page_limit(101) is True
    assert is_over_hard_page_limit(100) is False
    assert is_over_hard_page_limit(1) is False


def test_is_over_hard_page_limit_disabled_when_none(settings):
    settings.SEARCH_MAX_PAGE_HARD_LIMIT = None
    assert is_over_hard_page_limit(99999) is False
