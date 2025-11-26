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
from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse

from tags.models import FS1Tag, Tag
from utils.search import SearchResults, SearchResultsPaginator


def create_fake_search_engine_results():
    return SearchResults(
        facets={
            "tags": [
                ("synth", 100),
                ("analogue", 50),
                ("field-recording", 30),
                ("test", 20),
                ("driven", 10),
                ("development", 5),
            ],
        },
    )


def create_fake_perform_search_engine_query_response(num_results):
    results = create_fake_search_engine_results()
    results.docs = [
        {
            "group_docs": [{"id": sound_id}],
            "id": sound_id,
            "n_more_in_group": 0,
            "group_name": f"{pack_id}_xyz" if pack_id is not None else str(sound_id),
        }
        for sound_id, pack_id in zip(range(num_results, 2), range(num_results))
    ]
    paginator = SearchResultsPaginator(results, num_results)
    return results, paginator


class TagsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.tag1 = Tag.objects.create(name="testtag1")
        self.tag2 = Tag.objects.create(name="testtag2")
        self.NUM_RESULTS = 15
        self.perform_search_engine_query_response = create_fake_perform_search_engine_query_response(self.NUM_RESULTS)

    @mock.patch("tags.views.perform_search_engine_query")
    def test_tags_view_without_tags(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response

        response = self.client.get(reverse("tags"))
        perform_search_engine_query.assert_called()
        self.assertTemplateUsed(response, "tags/tag_cloud.html")
        self.assertContains(response, "Choose a tag to start browsing")

    @mock.patch("tags.views.cache")
    def test_tags_view_without_tags_cache(self, cache):
        cache.get.return_value = [
            {"name": "synth", "count": 707, "browse_url": "/browse/tags/synth/"},
            {"name": "analogue", "count": 514, "browse_url": "/browse/tags/analogue/"},
            {"name": "multisample", "count": 513, "browse_url": "/browse/tags/multisample/"},
        ]

        response = self.client.get(reverse("tags"))
        cache.get.assert_called()
        self.assertContains(response, "Choose a tag to start browsing")
        self.assertContains(response, "synth")
        self.assertTemplateUsed(response, "tags/tag_cloud.html")

    @mock.patch("tags.views.perform_search_engine_query")
    def test_tags_view_with_multiple_tags(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response
        response = self.client.get(reverse("tags", args=["synth/analogue"]))
        self.assertEqual(response.status_code, 302)


class OldTagLinksRedirectTestCase(TestCase):
    fixtures = ["fs1tags"]

    def setUp(self):
        self.fs1tags = [tag.fs1_id for tag in FS1Tag.objects.all()[0:2]]

    def test_old_tag_link_redirect_single_ok(self):
        # 301 permanent redirect, single tag result exists
        response = self.client.get(reverse("old-tag-page"), data={"id": self.fs1tags[0]})
        self.assertEqual(response.status_code, 301)

    def test_old_tag_link_redirect_multi_ok(self):
        # 301 permanent redirect, multiple tags result exists
        ids = "_".join([str(temp) for temp in self.fs1tags])
        response = self.client.get(reverse("old-tag-page"), data={"id": ids})
        self.assertEqual(response.status_code, 301)

    def test_old_tag_link_redirect_partial_ids_list(self):
        # 301 permanent redirect, one of the tags in the list exists
        partial_ids = str(self.fs1tags[0]) + "_0"
        response = self.client.get(reverse("old-tag-page"), data={"id": partial_ids})
        self.assertEqual(response.status_code, 301)

    def test_old_tag_link_redirect_not_exists_id(self):
        # 404 id exists does not exist
        response = self.client.get(reverse("old-tag-page"), data={"id": 0}, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_old_tag_link_redirect_invalid_id(self):
        # 404 invalid id
        response = self.client.get(reverse("old-tag-page"), data={"id": "invalid_id"}, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_old_tag_link_redirect_partial_invalid_id(self):
        # 404 invalid id in the id list
        partial_ids = str(self.fs1tags[0]) + "_invalidValue"
        response = self.client.get(reverse("old-tag-page"), data={"id": partial_ids}, follow=True)
        self.assertEqual(response.status_code, 404)
