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

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from models import Forum, Thread, Post


class ForumPostSignalTestCase(TestCase):
    """Tests for the pre/post save signals on Forum, Thread, and Post objects"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
        self.forum = Forum.objects.create(name="testForum", name_slug="test_forum", description="test")
        self.thread = Thread.objects.create(forum=self.forum, title="testThread", author=self.user)

    def test_add_unmoderated_post(self):
        """Some users' posts are created unmoderated, this should not update summary values"""

        self.assertEqual(self.thread.num_posts, 0)
        self.assertEqual(self.forum.num_posts, 0)
        post = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="NM")

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 0)
        self.forum.refresh_from_db()
        self.assertEqual(self.forum.num_posts, 0)

    def test_add_moderated_post(self):
        """Whitelisted users' posts are automatically moderated OK and immediately available.
        The default moderation state is OK
        """

        self.assertEqual(self.thread.num_posts, 0)
        self.assertEqual(self.forum.num_posts, 0)
        post = Post.objects.create(thread=self.thread, author=self.user, body="")

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 1)
        self.assertEqual(self.thread.last_post, post)
        self.forum.refresh_from_db()
        self.assertEqual(self.forum.num_posts, 1)
        self.assertEqual(self.forum.last_post, post)

    def test_moderate_post(self):
        """A post whose moderation status is changed to OK causes counts to increase"""

        post = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="NM")

        self.thread.refresh_from_db()
        # Thread initially has no posts...
        self.assertEqual(self.thread.num_posts, 0)

        post.moderation_state = "OK"
        post.save()

        # But after post moderation it has one
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 1)
        self.assertEqual(self.thread.last_post, post)

    def test_moderate_post_not_lastest(self):
        """When a post is moderated, it might not be the most recent post of a thread or forum"""

        firstpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="NM")
        secondpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")

        self.thread.refresh_from_db()
        # Last post of the thread is the most recently created one
        self.assertEqual(self.thread.last_post, secondpost)

        firstpost.moderation_state = "OK"
        firstpost.save()

        # After the first post is moderated, last post of the thread is still the most recent one
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 2)
        self.assertEqual(self.thread.last_post, secondpost)

    def test_remove_moderated_post(self):
        """Removing a moderated post decreses count and might change last_post"""

        firstpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")
        secondpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")
        thirdpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 3)
        self.assertEqual(self.thread.last_post, thirdpost)

        thirdpost.delete()

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 2)
        self.assertEqual(self.thread.last_post, secondpost)

        firstpost.delete()

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 1)
        self.assertEqual(self.thread.last_post, secondpost)

    def test_remove_unmoderated_post(self):
        """Removing an unmoderated post does not decrese count or change last_post"""

        firstpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")
        secondpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="NM")

        self.thread.refresh_from_db()
        # Last post of the thread is the moderated one
        self.assertEqual(self.thread.num_posts, 1)
        self.assertEqual(self.thread.last_post, firstpost)

        secondpost.delete()

        # After the unmoderated post is deleted, no values on the thread have changed
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 1)
        self.assertEqual(self.thread.last_post, firstpost)

    def test_remove_last_post_moderated(self):
        """If the last post of a thread is deleted, the thread is removed"""

        post = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 1)

        post.delete()

        with self.assertRaises(Thread.DoesNotExist):
            self.thread.refresh_from_db()

    def test_remove_last_post_unmoderated(self):
        """If there is still an unmoderated post on a thread, the thread is not removed"""

        modpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")
        unmodpost = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="NM")

        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 1)

        modpost.delete()

        # The thread still exists, but it has no post data
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.num_posts, 0)
        self.assertEqual(self.thread.last_post, None)

    def test_remove_post_last_in_thread_not_in_forum(self):
        """If the last post of a thread is removed, the last post of the forum may be
        from a different thread"""

        otherthread = Thread.objects.create(forum=self.forum, title="Another thread", author=self.user)

        t1post1 = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")
        t1post2 = Post.objects.create(thread=self.thread, author=self.user, body="", moderation_state="OK")
        t2post = Post.objects.create(thread=otherthread, author=self.user, body="", moderation_state="OK")

        self.thread.refresh_from_db()
        otherthread.refresh_from_db()
        self.forum.refresh_from_db()

        self.assertEqual(self.thread.last_post, t1post2)
        self.assertEqual(otherthread.last_post, t2post)
        self.assertEqual(self.forum.last_post, t2post)

        t1post2.delete()

        self.thread.refresh_from_db()
        otherthread.refresh_from_db()
        self.forum.refresh_from_db()

        # After deleting t1post2, the last post of thread1 has changed, but not the last post of the forum
        self.assertEqual(self.thread.last_post, t1post1)
        self.assertEqual(self.forum.last_post, t2post)


class ForumThreadSignalTestCase(TestCase):
    """Test signals of the Thread object"""

    def test_add_and_remove_thread(self):
        # Add new Thread and check if signal updates num_threads value

        user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
        forum = Forum.objects.create(name="Second Forum", name_slug="second_forum", description="another forum")

        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 0)
        thread = Thread.objects.create(forum=forum, title="testThread", author=user)
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 1)

        thread2 = Thread.objects.create(forum=forum, title="testThread", author=user)
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 2)

        # Now remove one thread and check if the values are updated correctly
        thread2.delete()
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 1)

        # Now remove the last threads and check if the values are updated correctly
        thread.delete()
        forum.refresh_from_db()
        self.assertEqual(forum.num_threads, 0)


class ForumTestCase(TestCase):

    def test_cant_view_unmoderated_post(self):
        """If a thread only has an unmoderated post, visting the thread with the client results in HTTP404"""

        user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
        forum = Forum.objects.create(name="Second Forum", name_slug="second_forum", description="another forum")
        thread = Thread.objects.create(forum=forum, title="testThread", author=user)

        Post.objects.create(thread=thread, author=user, body="", moderation_state="NM")

        res = self.client.get(reverse("forums-thread",
                                      kwargs={"forum_name_slug": forum.name_slug, "thread_id": thread.id}))
        self.assertEqual(res.status_code, 404)
