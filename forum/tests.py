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

from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth.models import User
from django.urls import reverse
from forum.models import Forum, Thread, Post, Subscription


def _create_forums_threads_posts(author, n_forums=1, n_threads=1, n_posts=5):
    for i in range(0, n_forums):
        forum = Forum.objects.create(
            name='Forum %i' % i,
            name_slug='forum_%i' % i,
            description="Description of forum %i" % i
        )
        for j in range(0, n_threads):
            thread = Thread.objects.create(
                author=author,
                title='Thread %i of forum %i' % (j, i),
                forum=forum
            )
            for k in range(0, n_posts):
                post = Post.objects.create(
                    author=author,
                    thread=thread,
                    body='Text of the post %i for thread %i and forum %i' % (k, j, i)
                )
                if k == 0:
                    thread.first_post = post
                    thread.save()


class ForumPageResponses(TestCase):

    def setUp(self):
        self.N_FORUMS = 1
        self.N_THREADS = 1
        self.N_POSTS = 5
        self.user = User.objects.create_user(username='testuser', email='email@example.com', password='12345')
        _create_forums_threads_posts(self.user, self.N_FORUMS, self.N_THREADS, self.N_POSTS)

    def test_forums_response_ok(self):
        resp = self.client.get(reverse('forums-forums'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['forums']), self.N_FORUMS)  # Check that N_FORUMS are passed to context

    def test_forum_response_ok(self):
        forum = Forum.objects.first()
        resp = self.client.get(reverse('forums-forum', args=[forum.name_slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['page'].object_list), self.N_THREADS)  # Check N_THREADS in context

    @override_settings(LAST_FORUM_POST_MINIMUM_TIME=0)
    def test_new_thread_response_ok(self):
        forum = Forum.objects.first()

        # Assert non-logged in user is redirected to login page
        resp = self.client.post(reverse('forums-new-thread', args=[forum.name_slug]), data={
            u'body': [u'New thread body (first post)'], u'subscribe': [u'on'], u'title': [u'New thread title']
        })
        self.assertRedirects(resp, '%s?next=%s' % (
            reverse('login'), reverse('forums-new-thread', args=[forum.name_slug])))

        # Assert logged in user can create new thread
        self.client.force_login(self.user)
        resp = self.client.post(reverse('forums-new-thread', args=[forum.name_slug]), data={
            u'body': [u'New thread body (first post)'], u'subscribe': [u'on'], u'title': [u'New thread title']
        })
        post = Post.objects.get(body=u'New thread body (first post)')
        self.assertRedirects(resp, post.get_absolute_url(), target_status_code=302)

    def test_thread_response_ok(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()
        resp = self.client.get(reverse('forums-thread', args=[forum.name_slug, thread.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['page'].object_list), self.N_POSTS)  # Check N_POSTS in context

    def test_post_response_ok(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()
        post = thread.post_set.first()
        resp = self.client.get(reverse('forums-post', args=[forum.name_slug, thread.id, post.id]))
        redirected_url = post.thread.get_absolute_url() + "?page=%d#post%d" % (1, post.id)
        self.assertRedirects(resp, redirected_url)

    @override_settings(LAST_FORUM_POST_MINIMUM_TIME=0)
    def test_thread_reply_response_ok(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()

        # Assert non-logged in user is redirected to login page
        resp = self.client.post(reverse('forums-reply', args=[forum.name_slug, thread.id]), data={
            u'body': [u'Reply post body'], u'subscribe': [u'on'],
        })
        self.assertRedirects(resp, '%s?next=%s' % (
            reverse('login'), reverse('forums-reply', args=[forum.name_slug, thread.id])))

        # Assert logged in user can reply
        self.client.force_login(self.user)
        resp = self.client.post(reverse('forums-reply', args=[forum.name_slug, thread.id]), data={
            u'body': [u'Reply post body'], u'subscribe': [u'on'],
        })
        post = Post.objects.get(body=u'Reply post body')
        self.assertRedirects(resp, post.get_absolute_url(), target_status_code=302)

    @override_settings(LAST_FORUM_POST_MINIMUM_TIME=0)
    def test_thread_reply_quote_post_response_ok(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()
        post = thread.post_set.first()

        # Assert non-logged in user is redirected to login page
        resp = self.client.post(reverse('forums-reply-quote', args=[forum.name_slug, thread.id, post.id]), data={
            u'body': [u'Reply post body'], u'subscribe': [u'on'],
        })
        self.assertRedirects(resp, '%s?next=%s' % (
            reverse('login'), reverse('forums-reply-quote', args=[forum.name_slug, thread.id, post.id])))

        # Assert logged in user can reply
        self.client.force_login(self.user)
        resp = self.client.post(reverse('forums-reply-quote', args=[forum.name_slug, thread.id, post.id]), data={
            u'body': [u'Reply post body'], u'subscribe': [u'on'],
        })
        post = Post.objects.get(body=u'Reply post body')
        self.assertRedirects(resp, post.get_absolute_url(), target_status_code=302)

    def test_edit_post_response_ok(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()
        post = thread.post_set.first()

        # Assert non-logged in user can't edit post
        resp = self.client.post(reverse('forums-post-edit', args=[post.id]), data={
            u'body': [u'Edited post body']
        })
        self.assertRedirects(resp, '%s?next=%s' % (reverse('login'), reverse('forums-post-edit', args=[post.id])))

        # Assert logged in user which is not author of post can't edit post
        user2 = User.objects.create_user(username='testuser2', email='email2@example.com', password='12345')
        self.client.force_login(user2)
        resp = self.client.post(reverse('forums-post-edit', args=[post.id]), data={
            u'body': [u'Edited post body']
        })
        self.assertEqual(resp.status_code, 404)

        # Assert logged in user can edit post
        self.client.force_login(self.user)
        resp = self.client.post(reverse('forums-post-edit', args=[post.id]), data={
            u'body': [u'Edited post body']
        })
        self.assertRedirects(resp, post.get_absolute_url(), target_status_code=302)
        edited_post = Post.objects.get(id=post.id)
        self.assertEquals(edited_post.body, u'Edited post body')

    def test_delete_post_response_ok(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()
        post = thread.post_set.first()

        # Assert non-logged in user can't delete post
        resp = self.client.get(reverse('forums-post-delete', args=[post.id]))
        self.assertRedirects(resp, '%s?next=%s' % (reverse('login'), reverse('forums-post-delete', args=[post.id])))

        # Assert logged in user which is not author of post can't delete post
        user2 = User.objects.create_user(username='testuser2', email='email2@example.com', password='12345')
        self.client.force_login(user2)
        resp = self.client.get(reverse('forums-post-delete', args=[post.id]))
        self.assertEqual(resp.status_code, 404)

        # Assert logged in user can delete post (see delete confirmation page)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('forums-post-delete', args=[post.id]))
        self.assertEquals(resp.status_code, 200)

    def test_delete_post_confirm_response_ok(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()
        post = thread.post_set.last()

        # Assert non-logged in user can't delete post
        resp = self.client.get(reverse('forums-post-delete-confirm', args=[post.id]))
        self.assertRedirects(resp, '%s?next=%s' % (reverse('login'), reverse('forums-post-delete-confirm', args=[post.id])))

        # Assert logged in user which is not author of post can't delete post
        user2 = User.objects.create_user(username='testuser2', email='email2@example.com', password='12345')
        self.client.force_login(user2)
        resp = self.client.get(reverse('forums-post-delete-confirm', args=[post.id]))
        self.assertEqual(resp.status_code, 404)

        # Assert logged in user can delete post
        self.client.force_login(self.user)
        resp = self.client.get(reverse('forums-post-delete-confirm', args=[post.id]))
        new_last_post = thread.post_set.last()
        self.assertRedirects(resp, new_last_post.get_absolute_url(), target_status_code=302)
        # TODO: this case only checks the deletion of the last post of a thread. Deleting the first post of a thread
        # TODO: (or the only post if there's only one) raises a 500 error. This should be fixed and test updated.

    def test_user_subscribe_to_thread(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()

        # Assert non-logged in user can't subscribe
        resp = self.client.get(reverse('forums-thread-subscribe', args=[forum.name_slug, thread.id]))
        self.assertRedirects(resp, '%s?next=%s' % (reverse('login'), reverse('forums-thread-subscribe', args=[forum.name_slug, thread.id])))

        # Assert logged in user can subscribe
        user2 = User.objects.create_user(username='testuser2', email='email2@example.com', password='12345')
        self.client.force_login(user2)
        resp = self.client.get(reverse('forums-thread-subscribe', args=[forum.name_slug, thread.id]))
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(Subscription.objects.filter(thread=thread, subscriber=user2).count(), 1)

        # Try to create another subscription for the same user and thread, it should not create it
        resp = self.client.get(reverse('forums-thread-subscribe', args=[forum.name_slug, thread.id]))
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(Subscription.objects.filter(thread=thread, subscriber=user2).count(), 1)

        # Assert logged in user can unsubscribe
        resp = self.client.get(reverse('forums-thread-unsubscribe', args=[forum.name_slug, thread.id]))
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(Subscription.objects.filter(thread=thread, subscriber=user2).count(), 0)

    def test_emails_sent_for_subscription_to_thread(self):
        forum = Forum.objects.first()
        thread = forum.thread_set.first()
        post = thread.post_set.first()

        self.client.force_login(self.user)
        resp = self.client.get(reverse('forums-thread-subscribe', args=[forum.name_slug, thread.id]))
        self.assertEqual(Subscription.objects.filter(thread=thread, subscriber=self.user).count(), 1)

        # User creates new post
        user2 = User.objects.create_user(username='testuser2', email='email2@example.com', password='12345')
        self.client.force_login(user2)

        resp = self.client.get(reverse('forums-thread-subscribe', args=[forum.name_slug, thread.id]))
        self.assertEqual(Subscription.objects.filter(thread=thread, subscriber=user2).count(), 1)

        resp = self.client.post(reverse('forums-reply-quote', args=[forum.name_slug, thread.id, post.id]), data={
            u'body': [u'Reply post body'], u'subscribe': [u'on'],
        })
        post = Post.objects.get(body=u'Reply post body')
        self.assertRedirects(resp, post.get_absolute_url(), target_status_code=302)

        # Both users are subscribed but the email is not sent to the user that is sending the post
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[freesound] topic reply notification - Thread 0 of forum 0")

