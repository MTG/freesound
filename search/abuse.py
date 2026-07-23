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

from django.conf import settings


class PaginationAbuseBlocked(Exception):
    """raised if a request has an invalid pagination value"""


def is_over_hard_page_limit(page: int):
    """True if the requested page exceeds the configured maximum page limit.

    Returns False (is disabled) when ``SEARCH_MAX_PAGE_HARD_LIMIT`` is None.
    """
    limit = settings.SEARCH_MAX_PAGE_HARD_LIMIT
    return limit is not None and page > limit
