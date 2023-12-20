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

from functools import cached_property

from django.core.paginator import Paginator
from django.contrib.admin.views.main import ChangeList
from django.db import connection


class NoPkDescOrderedChangeList(ChangeList):

    def get_ordering(self, request, queryset):
        rv = super().get_ordering(request, queryset)
        rv = list(rv)
        rv.remove('-pk') if '-pk' in rv else None
        return tuple(rv)


class LargeTablePaginator(Paginator):
    """ We use the information on postgres table 'reltuples' to avoid using count(*) for performance. """

    @cached_property
    def count(self):
        try:
            if not self.object_list.query.where:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT reltuples FROM pg_class WHERE relname = %s", [self.object_list.query.model._meta.db_table]
                )
                ret = int(cursor.fetchone()[0])
                return ret
            else:
                return self.object_list.count()
        except:
            # AttributeError if object_list has no count() method.
            return len(self.object_list)
