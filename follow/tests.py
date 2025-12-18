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

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from follow.models import FollowingQueryItem, FollowingUserItem


class FollowTestCase(TestCase):
    fixtures = ["users", "follow"]

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass")
        self.client.force_login(self.user)

    def test_following_users(self):
        # If we get following users for someone who exists, OK
        resp = self.client.get(reverse("user-following-users", args=["User2"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)

        # Someone who doesn't exist should give 404
        resp = self.client.get(reverse("user-following-users", args=["User32"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 404)

    def test_following_users_oldusername(self):
        user = User.objects.get(username="User2")
        user.username = "new-username"
        user.save()
        # If we get following users for someone who exists by it's old username
        resp = self.client.get(reverse("user-following-users", args=["User2"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 301)

    def test_followers_modal(self):
        # If we get following users for someone who exists, OK
        resp = self.client.get(reverse("user-followers", args=["User2"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "User2's followers")

        # Someone who doesn't exist should give 404
        resp = self.client.get(reverse("user-followers", args=["User32"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 404)

    def test_followers_oldusername(self):
        user = User.objects.get(username="User2")
        user.username = "new-username"
        user.save()
        # If we get following users for someone who exists by it's old username
        resp = self.client.get(reverse("user-followers", args=["User2"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 301)

    def test_following_tags(self):
        # If we get following tags for someone who exists, OK
        resp = self.client.get(reverse("user-following-tags", args=["User2"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 200)

        # Someone who doesn't exist should give 404
        resp = self.client.get(reverse("user-following-tags", args=["User32"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 404)

    def test_following_tags_oldusername(self):
        user = User.objects.get(username="User2")
        user.username = "new-username"
        user.save()
        # If we get following tags for someone who exists by it's old username
        resp = self.client.get(reverse("user-following-tags", args=["User2"]) + "?ajax=1")
        self.assertEqual(resp.status_code, 301)

    def test_follow_user(self):
        # Start following unexisting user
        resp = self.client.get(reverse("follow-user", args=["nouser"]))
        self.assertEqual(resp.status_code, 404)

        # Start following existing user
        resp = self.client.get(reverse("follow-user", args=["User1"]))
        self.assertEqual(resp.status_code, 200)

        # Start following user you already follow
        resp = self.client.get(reverse("follow-user", args=["User1"]))
        self.assertEqual(resp.status_code, 200)

        # Check that user is actually following the other user
        self.assertEqual(
            FollowingUserItem.objects.filter(user_from__username="testuser", user_to__username="User1").exists(), True
        )

        # Stop following unexisting user
        resp = self.client.get(reverse("unfollow-user", args=["nouser"]))
        self.assertEqual(resp.status_code, 404)

        # Stop following user you are not actually following
        resp = self.client.get(reverse("unfollow-user", args=["User1"]))
        self.assertEqual(resp.status_code, 200)

        # Stop following user you follow
        resp = self.client.get(reverse("unfollow-user", args=["User1"]))
        self.assertEqual(resp.status_code, 200)

        # Check that user is no longer following the other user
        self.assertEqual(
            FollowingUserItem.objects.filter(user_from__username="testuser", user_to__username="User1").exists(), False
        )

    def test_follow_tags(self):
        # Start following group of tags
        resp = self.client.get(reverse("follow-tags", args=["field-recording/another_tag"]))
        self.assertEqual(resp.status_code, 200)

        # Start following group of tags you already follow
        resp = self.client.get(reverse("follow-tags", args=["field-recording/another_tag"]))
        self.assertEqual(resp.status_code, 200)

        # Check that user is actually following the tags
        self.assertEqual(
            FollowingQueryItem.objects.filter(user__username="testuser", query="field-recording another_tag").exists(),
            True,
        )

        # Stop following group of tags you do not already follow
        resp = self.client.get(reverse("unfollow-tags", args=["a-tag/another_tag"]))
        self.assertEqual(resp.status_code, 200)

        # Stop following group of tags you already follow
        resp = self.client.get(reverse("unfollow-tags", args=["field-recording/another_tag"]))
        self.assertEqual(resp.status_code, 200)

        # Check that user is no longer following the tags
        self.assertEqual(
            FollowingQueryItem.objects.filter(user__username="testuser", query="field-recording another_tag").exists(),
            False,
        )

    def test_stream(self):
        # Stream should return OK
        resp = self.client.get(reverse("stream"))
        self.assertEqual(resp.status_code, 200)


class StreamViewTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="stream-user", password="pwd12345")
        self.client.force_login(self.user)
        self.more_params = ["filter", "sort"]
        self.tags = ["field-recording"]
        self.stream_response = (
            [(self.user, [], self.more_params, 0, 0)],
            [(self.tags, [], self.more_params, 0, 0)],
        )
        self.build_patcher = patch("follow.views.follow_utils.build_time_lapse", return_value="MOCK_TIME_LAPSE")
        self.get_patcher = patch("follow.views.follow_utils.get_stream_sounds", return_value=self.stream_response)
        self.mock_build_time_lapse = self.build_patcher.start()
        self.mock_get_stream_sounds = self.get_patcher.start()

    def tearDown(self):
        self.build_patcher.stop()
        self.get_patcher.stop()
        super().tearDown()

    def _reset_mocks(self):
        self.mock_build_time_lapse.reset_mock()
        self.mock_get_stream_sounds.reset_mock()
        self.mock_get_stream_sounds.return_value = self.stream_response

    def test_stream_get_uses_default_range(self):
        self._reset_mocks()
        response = self.client.get(reverse("stream"))

        self.assertEqual(response.status_code, 200)
        context = response.context[-1]
        self.mock_build_time_lapse.assert_called_once()
        self.mock_get_stream_sounds.assert_called_once_with(self.user, "MOCK_TIME_LAPSE", num_results_per_group=4)
        self.assertEqual(response.context["select_value"], "")
        self.assertEqual(response.context["users_sounds"][0][0], self.user)
        self.assertEqual(response.context["tags_sounds"][0][0], self.tags)

    def test_stream_post_time_lapse_option(self):
        self._reset_mocks()
        response = self.client.post(reverse("stream"), {"time_lapse": "last_week"})

        self.assertEqual(response.status_code, 200)
        self.mock_build_time_lapse.assert_called_once()
        self.mock_get_stream_sounds.assert_called_once_with(self.user, "MOCK_TIME_LAPSE", num_results_per_group=4)
        self.assertEqual(response.context["select_value"], "last_week")
        self.assertEqual(response.context["users_sounds"][0][0], self.user)

    def test_stream_post_specific_dates_option(self):
        self._reset_mocks()
        payload = {
            "time_lapse": "specific_dates",
            "date_from": "2024-01-02",
            "date_to": "2024-01-05",
        }
        response = self.client.post(reverse("stream"), payload)

        self.assertEqual(response.status_code, 200)
        self.mock_build_time_lapse.assert_not_called()
        expected_time_lapse = '["2024-01-02T00:00:00Z" TO "2024-01-05T23:59:59.999Z"]'
        self.mock_get_stream_sounds.assert_called_once_with(self.user, expected_time_lapse, num_results_per_group=4)
        self.assertEqual(response.context["date_from"], "2024-01-02")
        self.assertEqual(response.context["date_to"], "2024-01-05")

    def test_stream_post_specific_dates_missing_from(self):
        self._reset_mocks()
        payload = {
            "time_lapse": "specific_dates",
            "date_from": "",
            "date_to": "2024-01-05",
        }
        response = self.client.post(reverse("stream"), payload)

        self.assertEqual(response.status_code, 200)
        self.mock_build_time_lapse.assert_not_called()
        expected_date_from = "2023-12-29"
        expected_time_lapse = f'["{expected_date_from}T00:00:00Z" TO "2024-01-05T23:59:59.999Z"]'
        self.mock_get_stream_sounds.assert_called_once_with(self.user, expected_time_lapse, num_results_per_group=4)
        self.assertEqual(response.context["date_from"], expected_date_from)
        self.assertEqual(response.context["date_to"], "2024-01-05")
