# -*- coding: utf-8 -*-
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
from django.test import TestCase

from sounds.models import Sound
from utils.pagination import CountProvidedPaginator


class PaginationTest(TestCase):

    fixtures = ['licenses.json', 'sounds.json']

    def test_pagination_cache_count(self):
        """If you create a paginator, it'll call .count() once on the queryset
         to get the length, but not again when needing to use the number of items"""

        sounds = Sound.objects.all()

        with self.assertNumQueries(2):
            paginator = CountProvidedPaginator(sounds, 10)
            # Call count twice, should only run one query
            self.assertEquals(paginator.count, 14)
            self.assertEquals(paginator.count, 14)
            # and another query to evaluate the page. Call len() to force the qs to be evaluated
            first_page = paginator.page(1)
            self.assertEquals(len(first_page), 10)

    def test_pagination_provide_object_count(self):
        """If you pass a count into the paginator it won't call .count() on the queryset to
        get the count"""

        sounds = Sound.objects.all()

        with self.assertNumQueries(1):
            paginator = CountProvidedPaginator(sounds, 10, object_count=14)
            # Calls to .count will return the right value but won't cause a query to run
            self.assertEquals(paginator.count, 14)
            self.assertEquals(paginator.count, 14)
            # This should be the only query that runs, call len() to force the qs to be evaluated
            first_page = paginator.page(1)
            self.assertEquals(len(first_page), 10)
