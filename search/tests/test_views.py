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

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from sounds.models import Sound
from utils.pagination import PreSlicedCountProvidedPaginator
from utils.search import SearchResults
from utils.test_helpers import create_user_and_sounds


def create_fake_search_engine_results():
    return SearchResults(
        docs=[],  # Actual sounds to be returned are filled dynamically in tests
        num_found=548,
        start=0,
        num_rows=0,
        non_grouped_number_of_results=737,
        facets={
            "bitdepth": [("16", 390), ("24", 221), ("0", 105), ("32", 19), ("4", 1)],
            "bitrate": [("1411", 153), ("1378", 151), ("2250", 79), ("1500", 32), ("1536", 23)],
            "channels": [("2", 630), ("1", 91), ("6", 12), ("4", 4)],
        },
        highlighting={},
        q_time=17,
    )


def return_successful_clustering_results(sound_id_1, sound_id_2, sound_id_3, sound_id_4):
    return {
        "graph": {
            "directed": False,
            "graph": {},
            "nodes": [
                {"group_centrality": 0.5, "group": 0, "id": sound_id_1},
                {"group_centrality": 1, "group": 0, "id": sound_id_2},
                {"group_centrality": 0.5, "group": 1, "id": sound_id_3},
                {"group_centrality": 1, "group": 1, "id": sound_id_4},
            ],
            "links": [
                {"source": sound_id_1, "target": sound_id_2},
                {"source": sound_id_1, "target": sound_id_3},
                {"source": sound_id_3, "target": sound_id_4},
            ],
            "multigraph": False,
        },
        "finished": True,
        "clusters": [
            [sound_id_1, sound_id_2],
            [sound_id_3, sound_id_4],
        ],
        "cluster_ids": [23, 24],
        "cluster_names": ["tag1 tag2 tag3", "tag1 tag2 tag3"],
        "example_sounds_data": [["a"], ["b", "c"]],
    }


failed_clustering_results = None


def create_fake_perform_search_engine_query_response(num_results=15):
    # NOTE: this method needs Sound objects to have been created before running it (for example loading sounds_with_tags fixture)
    sound_ids = list(
        Sound.objects.filter(moderation_state="OK", processing_state="OK").values_list("id", "pack_id")[:num_results]
    )
    results = create_fake_search_engine_results()
    results.docs = [
        {
            "group_docs": [{"id": sound_id}],
            "id": sound_id,
            "n_more_in_group": 0,
            "group_name": f"{pack_id}_xyz" if pack_id is not None else "",
        }
        for sound_id, pack_id in sound_ids
    ]
    paginator = PreSlicedCountProvidedPaginator(results.docs, num_results, results.num_found)
    return (results, paginator)


class SearchPageTests(TestCase):
    fixtures = ["licenses", "users", "sounds_with_tags"]

    def setUp(self):
        # Generate a fake solr response data to mock perform_search_engine_query function
        self.NUM_RESULTS = 15
        self.perform_search_engine_query_response = create_fake_perform_search_engine_query_response(self.NUM_RESULTS)

    @mock.patch("search.views.perform_search_engine_query")
    def test_search_page_response_ok(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response

        # 200 response on sound search page access
        resp = self.client.get(reverse("sounds-search"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["error_text"], None)
        self.assertEqual(len(resp.context["docs"]), self.NUM_RESULTS)

    @mock.patch("search.views.perform_search_engine_query")
    def test_search_page_num_queries(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response

        # Check that we perform one single query to get all sounds' information and don't do one extra query per sound
        cache.clear()
        with self.assertNumQueries(1):
            self.client.get(reverse("sounds-search"))

        # Repeat the check when using the "grid display"
        cache.clear()
        with self.assertNumQueries(1):
            self.client.get(reverse("sounds-search") + "?cm=1")

        # When using search engine similarity, there'll be one extra query performed to get the similarity status of the sounds

        # Now check number of queries when displaying results as packs (i.e., searching for packs)
        cache.clear()
        with self.assertNumQueries(4):
            self.client.get(reverse("sounds-search") + "?dp=1")

        # Also check packs when displaying in grid mode
        cache.clear()
        with self.assertNumQueries(4):
            self.client.get(reverse("sounds-search") + "?dp=1&cm=1")


class SearchPageLowerClampTests(TestCase):
    """If ?page= value is < 1 then clamp it to 1 before sending to solr in order to prevent failures"""

    fixtures = ["licenses", "users", "sounds_with_tags"]

    def setUp(self):
        self.perform_search_engine_query_response = create_fake_perform_search_engine_query_response(15)

    @mock.patch("search.views.perform_search_engine_query")
    def test_sound_search_page_zero_clamped_before_query(self, perform_search_engine_query):
        perform_search_engine_query.return_value = self.perform_search_engine_query_response

        resp = self.client.get(reverse("sounds-search") + "?q=test&page=0")

        self.assertEqual(resp.status_code, 200)
        query_params = perform_search_engine_query.call_args[0][0]
        self.assertEqual(query_params["current_page"], 1)

    @mock.patch("search.views.get_search_engine")
    def test_forum_search_page_zero_clamped_before_query(self, get_search_engine):
        engine = get_search_engine.return_value
        engine.search_forum_posts.return_value = SearchResults(docs=[], num_found=0)

        resp = self.client.get(reverse("forums-search") + "?q=test&page=0")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(engine.search_forum_posts.call_args.kwargs["current_page"], 1)


class SearchOutOfRangeTests(TestCase):
    """If we ask for a page number past the number of available results then
    show a message instead of an empty page (rendering 0 items).
    Show a paginator with the last real page of results highlighted, but
    don't re-run the search on that page."""

    fixtures = ["licenses", "users", "sounds_with_tags"]

    @mock.patch("search.views.perform_search_engine_query")
    def test_sound_search_past_last_page_shows_message(self, perform_search_engine_query):
        # num_found > 0 but the requested (overflow) page returned no docs.
        results = SearchResults(docs=[], num_found=548)
        # this paginator has 37 pages
        paginator = PreSlicedCountProvidedPaginator(results.docs, 15, results.num_found)
        perform_search_engine_query.return_value = (results, paginator)

        # Out of range but within settings.SEARCH_MAX_PAGE_HARD_LIMIT
        resp = self.client.get(reverse("sounds-search") + "?q=test&page=99")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["beyond_last"])
        # actual last page, not what was requested
        self.assertEqual(resp.context["current_page"], 37)
        self.assertContains(resp, "No more results")
        self.assertNotContains(resp, "No results...")
        content = resp.content.decode()
        # in the paginator the last real page is the current page - no <a>
        self.assertInHTML('<li class="bw-pagination_circle bw-pagination_selected">37</li>', content)
        # page 1 link exists
        self.assertInHTML('<a href="/search/?q=test&amp;page=1#sound" data-page="1" title="First Page">1</a>', content)

    @mock.patch("search.views.perform_search_engine_query")
    def test_sound_search_zero_results_shows_no_results(self, perform_search_engine_query):
        results = SearchResults(docs=[], num_found=0)
        paginator = PreSlicedCountProvidedPaginator(results.docs, 15, results.num_found)
        perform_search_engine_query.return_value = (results, paginator)

        resp = self.client.get(reverse("sounds-search") + "?q=nonsense")

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["beyond_last"])
        self.assertContains(resp, "No results...")
        self.assertNotContains(resp, "No more results")
        # 0 results shows no paginator
        self.assertNotContains(resp, "bw-pagination_container")

    @mock.patch("search.views.get_search_engine")
    def test_forum_search_past_last_page_shows_no_more_results(self, get_search_engine):
        engine = get_search_engine.return_value
        engine.search_forum_posts.return_value = SearchResults(docs=[], num_found=100)

        resp = self.client.get(reverse("forums-search") + "?q=test&page=999")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["beyond_last"])
        self.assertContains(resp, "No more results")
        self.assertNotContains(resp, "No results...")
        # actual last page (100 posts / 20 per page), not what was requested
        self.assertEqual(resp.context["current_page"], 5)
        content = resp.content.decode()
        # in the paginator the last real page is the current page - no <a>
        self.assertInHTML('<li class="bw-pagination_circle bw-pagination_selected">5</li>', content)
        # page 1 link exists
        self.assertInHTML(
            '<a href="/forum/forums-search/?q=test&amp;page=1" data-page="1" title="Page 1">1</a>', content
        )

    @mock.patch("search.views.get_search_engine")
    def test_forum_search_zero_results_shows_no_results(self, get_search_engine):
        engine = get_search_engine.return_value
        engine.search_forum_posts.return_value = SearchResults(docs=[], num_found=0)

        resp = self.client.get(reverse("forums-search") + "?q=nonsense")

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["beyond_last"])
        self.assertContains(resp, "No results...")
        self.assertNotContains(resp, "No more results")
        # 0 results shows no paginator
        self.assertNotContains(resp, "bw-pagination_container")


class SearchResultClustering(TestCase):
    fixtures = ["licenses"]

    def setUp(self):
        _, _, sounds = create_user_and_sounds(num_sounds=4, tags="tag1, tag2, tag3")
        sound_ids = []
        sound_id_preview_urls = []
        for sound in sounds:
            sound_ids.append(str(sound.id))
            sound_id_preview_urls.append((sound.id, sound.locations()["preview"]["LQ"]["ogg"]["url"]))

        self.sound_id_preview_urls = sound_id_preview_urls
        self.successful_clustering_results = return_successful_clustering_results(*sound_ids)
        self.num_sounds_clustering_results = [2, 2]
        self.failed_clustering_results = failed_clustering_results

    @mock.patch("search.views.get_num_sounds_per_cluster")
    @mock.patch("search.views.get_clusters_for_query")
    def test_successful_search_result_clustering_view(self, get_clusters_for_query, get_num_sounds_per_cluster):
        get_clusters_for_query.return_value = self.successful_clustering_results
        get_num_sounds_per_cluster.return_value = self.num_sounds_clustering_results
        resp = self.client.get(reverse("clusters-section"))

        # 200 status code & use of clustering facets template
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "search/clustering_results.html")

        # check cluster's content
        self.assertEqual(
            resp.context["clusters_data"], [(23, 2, "tag1 tag2 tag3", ["a"]), (24, 2, "tag1 tag2 tag3", ["b", "c"])]
        )

    @mock.patch("search.views.get_num_sounds_per_cluster")
    @mock.patch("search.views.get_clusters_for_query")
    def test_failed_search_result_clustering_view(self, get_clusters_for_query, get_num_sounds_per_cluster):
        get_clusters_for_query.return_value = self.failed_clustering_results
        get_num_sounds_per_cluster.return_value = self.num_sounds_clustering_results
        resp = self.client.get(reverse("clusters-section"))

        # 200 status code & JSON response content
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "search/clustering_results.html")
        self.assertEqual(resp.context["clusters_data"], None)


@pytest.mark.django_db
class TestSearchDeepPagination:
    IP = {"HTTP_X_FORWARDED_FOR": "8.8.8.8"}

    def test_hard_cap_blocks_page_over_limit_for_everyone(self, client):
        # Max page limit applies to anonymous and signed in users. Both search page and tag search page
        call_command("loaddata", "users")
        search_url = reverse("sounds-search") + "?q=wind&page=300"
        tag_url = reverse("tags") + '?f=tag:"field-recording"&page=300'

        with mock.patch("search.views.perform_search_engine_query") as perform:
            assert client.get(search_url, **self.IP).status_code == 429
            assert client.get(tag_url, **self.IP).status_code == 429

            client.force_login(User.objects.get(username="User1"))
            assert client.get(search_url, **self.IP).status_code == 429

            perform.assert_not_called()

    def test_tags_cloud_ignores_page_param(self, client):
        # base tag cloud page with no query shouldn't limit on large page (because it does no pagination).
        cache.set("initial_tagcloud", [])
        with mock.patch("search.views.perform_search_engine_query") as perform:
            assert client.get(reverse("tags") + "?page=300", **self.IP).status_code == 200
            perform.assert_not_called()

    def test_hard_cap_disabled_when_setting_is_none(self, client, settings):
        call_command("loaddata", "licenses", "users", "sounds_with_tags")
        settings.SEARCH_MAX_PAGE_HARD_LIMIT = None
        with mock.patch("search.views.perform_search_engine_query") as perform:
            perform.return_value = create_fake_perform_search_engine_query_response(15)
            resp = client.get(reverse("sounds-search") + "?q=wind&page=300", **self.IP)
            assert resp.status_code == 200
            perform.assert_called()
