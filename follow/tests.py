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
from django.contrib.auth.models import User
from django.test.client import Client

from accounts.models import Profile

class FollowTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass")
        self.profile = Profile.objects.create(user=self.user, wants_newsletter=True, accepted_tos=True)
        self.client = Client()

    def test_following_users(self):
        # If we get following users for someone who exists, OK
        resp = self.client.get("/people/testuser/following_users/")
        self.assertEqual(resp.status_code, 200)

        # Someone who doesn't exist should give 404
        resp = self.client.get("/people/nouser/following_users/")
        self.assertEqual(resp.status_code, 404)
