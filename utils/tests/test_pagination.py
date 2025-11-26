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
from django.core.management import call_command
from django.test import TestCase, RequestFactory
from django.urls import reverse

from sounds.models import Sound
from utils.pagination import CountProvidedPaginator, paginate
from general.templatetags.bw_templatetags import bw_paginator


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
        bw_paginator({}, paginator["paginator"], paginator["page"], paginator["current_page"], dummy_request)
