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

from django.core.paginator import Paginator, InvalidPage
from django.utils.functional import cached_property


class CountProvidedPaginator(Paginator):
    """ A django Paginator that takes an optional object_count
        which is the length of object_list. This means that count() or
        len() doesn't have to be called """

    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True, object_count=None):
        Paginator.__init__(self, object_list, per_page, orphans, allow_empty_first_page)

        self._count = object_count

    @cached_property
    def count(self):
        # If the count was provided return it, otherwise use the
        if self._count:
            return self._count
        return super().count


def paginate(request, qs, items_per_page=20, page_get_name='page', object_count=None):
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
