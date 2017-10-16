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
from models import Forum, Thread, Post
from django.contrib.auth.models import User


class ForumTestCase(TestCase):

    def test_add_and_remove_post(self):
        # Add new Post to Thread and check if signal updates num_posts value
        user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
        forum = Forum.objects.create(name="testForum", name_slug="test_forum", description="test")
        thread = Thread.objects.create(forum=forum, title="testThread", author=user)

        thread.refresh_from_db()
        self.assertEqual(thread.num_posts, 0)
        forum.refresh_from_db()
        self.assertEqual(forum.num_posts, 0)
        post = Post.objects.create(thread=thread, author=user, body="")
        thread.refresh_from_db()
        self.assertEqual(thread.num_posts, 1)
        forum.refresh_from_db()
        self.assertEqual(forum.num_posts, 1)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.num_posts, 1)

        post2 = Post.objects.create(thread=thread, author=user, body="")
        thread.refresh_from_db()
        self.assertEqual(thread.num_posts, 2)
        forum.refresh_from_db()
        self.assertEqual(forum.num_posts, 2)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.num_posts, 2)

        # Now remove one post and check if the values are updated correcly
        post2.delete()
        thread.refresh_from_db()
        self.assertEqual(thread.num_posts, 1)
        forum.refresh_from_db()
        self.assertEqual(forum.num_posts, 1)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.num_posts, 1)

        # Now remove the last post and check if the values are updated correcly
        post.delete()
        forum.refresh_from_db()
        self.assertEqual(forum.num_posts, 0)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.num_posts, 0)

    def test_add_and_remove_thread(self):
        # Add new Thread and check if signal updates num_threads value
        user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
        forum = Forum.objects.create(name="testForum", name_slug="test_forum", description="test")

        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 0)
        thread = Thread.objects.create(forum=forum, title="testThread", author=user)
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 1)

        thread2 = Thread.objects.create(forum=forum, title="testThread", author=user)
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 2)

        # Now remove one thread and check if the values are updated correcly
        thread2.delete()
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 1)

        # Now remove the last threads and check if the values are updated correcly
        thread.delete()
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 0)


