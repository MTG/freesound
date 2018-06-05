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
from django.test.client import Client
from accounts.models import Profile
from django.contrib.auth.models import User
from follow.models import FollowingUserItem, FollowingQueryItem


class FollowTestCase(TestCase):

    fixtures = ['users', 'follow']

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass")
        self.user.profile.agree_to_gdpr()
        self.client.force_login(self.user)

    def test_following_users(self):
        # If we get following users for someone who exists, OK
        resp = self.client.get("/people/User2/following_users/")
        self.assertEqual(resp.status_code, 200)

        # Someone who doesn't exist should give 404
        resp = self.client.get("/people/nouser/following_users/")
        self.assertEqual(resp.status_code, 404)

    def test_following_users_oldusername(self):
        user = User.objects.get(username='User2')
        user.username = "new-username"
        user.save()
        # If we get following users for someone who exists by it's old username
        resp = self.client.get("/people/User2/following_users/")
        self.assertEqual(resp.status_code, 301)

    def test_followers(self):
        # If we get following users for someone who exists, OK
        resp = self.client.get("/people/User2/followers/")
        self.assertEqual(resp.status_code, 200)

        # Someone who doesn't exist should give 404
        resp = self.client.get("/people/nouser/followers/")
        self.assertEqual(resp.status_code, 404)

    def test_followers_oldusername(self):
        user = User.objects.get(username='User2')
        user.username = "new-username"
        user.save()
        # If we get following users for someone who exists by it's old username
        resp = self.client.get("/people/User2/followers/")
        self.assertEqual(resp.status_code, 301)

    def test_following_tags(self):
        # If we get following tags for someone who exists, OK
        resp = self.client.get("/people/User2/following_tags/")
        self.assertEqual(resp.status_code, 200)

        # Someone who doesn't exist should give 404
        resp = self.client.get("/people/nouser/following_tags/")
        self.assertEqual(resp.status_code, 404)

    def test_following_tags_oldusename(self):
        user = User.objects.get(username='User2')
        user.username = "new-username"
        user.save()
        # If we get following tags for someone who exists by it's old username
        resp = self.client.get("/people/User2/following_tags/")
        self.assertEqual(resp.status_code, 301)

    def test_follow_user(self):
        # Start following unexisting user
        resp = self.client.get("/follow/follow_user/nouser/")
        self.assertEqual(resp.status_code, 404)

        # Start following existing user
        resp = self.client.get("/follow/follow_user/User1/")
        self.assertEqual(resp.status_code, 200)

        # Start following user you already follow
        resp = self.client.get("/follow/follow_user/User1/")
        self.assertEqual(resp.status_code, 200)

        # Check that user is actually following the other user
        self.assertEqual(
            FollowingUserItem.objects.filter(user_from__username='testuser', user_to__username='User1').exists(), True)

        # Stop following unexisting user
        resp = self.client.get("/follow/unfollow_user/nouser/")
        self.assertEqual(resp.status_code, 404)

        # Stop following user you are not actually following
        resp = self.client.get("/follow/unfollow_user/User3/")
        self.assertEqual(resp.status_code, 200)

        # Stop following user you follow
        resp = self.client.get("/follow/unfollow_user/User1/")
        self.assertEqual(resp.status_code, 200)

        # Check that user is no longer following the other user
        self.assertEqual(
            FollowingUserItem.objects.filter(user_from__username='testuser', user_to__username='User1').exists(), False)

    def test_follow_tags(self):
        # Start following group of tags
        resp = self.client.get("/follow/follow_tags/field-recording/another_tag/")
        self.assertEqual(resp.status_code, 200)

        # Start following group of tags you already follow
        resp = self.client.get("/follow/follow_tags/field-recording/another_tag/")
        self.assertEqual(resp.status_code, 200)

        # Check that user is actually following the tags
        self.assertEqual(
            FollowingQueryItem.objects.filter(user__username='testuser', query='field-recording another_tag').exists(), True)

        # Stop following group of tags you do not already follow
        resp = self.client.get("/follow/unfollow_tags/a-tag/another_tag/")
        self.assertEqual(resp.status_code, 200)

        # Stop following group of tags you already follow
        resp = self.client.get("/follow/unfollow_tags/field-recording/another_tag/")
        self.assertEqual(resp.status_code, 200)

        # Check that user is no longer following the tags
        self.assertEqual(
            FollowingQueryItem.objects.filter(user__username='testuser', query='field-recording another_tag').exists(), False)

    def test_stream(self):
        # Stream should return OK
        resp = self.client.get("/home/stream/")
        self.assertEqual(resp.status_code, 200)
