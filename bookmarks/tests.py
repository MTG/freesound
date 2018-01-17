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

import bookmarks.models


class BookmarksTest(TestCase):

    fixtures = ['sounds']

    def test_bookmarks_context(self):
        resp = self.client.get(reverse('bookmarks-for-user', kwargs={'username': 'Anton'}))
        context = resp.context

        self.assertEqual(200, resp.status_code)
        expected_keys = ['bookmark_categories', 'bookmarked_sounds', 'current_page', 'is_owner',
                         'n_uncat', 'page', 'paginator', 'user']
        context_keys = context.keys()
        for k in expected_keys:
            self.assertIn(k, context_keys)

    def test_no_such_bookmark_category(self):
        resp = self.client.get(reverse('bookmarks-for-user-for-category', kwargs={'username': 'Anton', 'category_id': 995}))

        self.assertEqual(404, resp.status_code)

    def test_no_user(self):
        resp = self.client.get(reverse('bookmarks-for-user', kwargs={'username': 'NoSuchUser'}))

        self.assertEqual(404, resp.status_code)

    def test_bookmarks_oldusername(self):
        user = User.objects.get(username='Anton')
        user.username = "new-username"
        user.save()
        # The response should be a 301
        resp = self.client.get(reverse('bookmarks-for-user', kwargs={'username': 'Anton'}))
        self.assertEqual(301, resp.status_code)

        # Now follow the redirect
        resp = self.client.get(reverse('bookmarks-for-user', kwargs={'username': 'Anton'}), follow=True)
        context = resp.context

        self.assertEqual(200, resp.status_code)
        expected_keys = ['bookmark_categories', 'bookmarked_sounds', 'current_page', 'is_owner',
                         'n_uncat', 'page', 'paginator', 'user']
        context_keys = context.keys()
        for k in expected_keys:
            self.assertIn(k, context_keys)

    def test_your_bookmarks(self):
        user = User.objects.get(username='Anton')
        self.client.force_login(user)

        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, name='BookmarkedSound')

        response = self.client.get(reverse('bookmarks-for-user', kwargs={'username': user.username}))

        self.assertEqual(200, response.status_code)
        self.assertEquals(3, len(response.context['bookmarked_sounds']))
        self.assertContains(response, 'Your bookmarks')
        self.assertContains(response, 'Uncategorized bookmarks')
        self.assertContains(response, 'BookmarkedSound')

    def test_others_bookmarks(self):
        logged_in_user = User.objects.get(username='Bram')
        self.client.force_login(logged_in_user)

        user = User.objects.get(username='Anton')
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, name='BookmarkedSound')

        response = self.client.get(reverse('bookmarks-for-user', kwargs={'username': user.username}))

        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Bookmarks by Anton')

    def test_no_bookmarks(self):
        user = User.objects.get(username='Anton')
        self.client.force_login(user)

        response = self.client.get(reverse('bookmarks-for-user', kwargs={'username': user.username}))

        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Your bookmarks')
        self.assertContains(response, 'There are no uncategorized bookmarks')

    def test_bookmark_category(self):
        user = User.objects.get(username='Anton')
        self.client.force_login(user)

        category = bookmarks.models.BookmarkCategory.objects.create(name='Category1', user=user)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11, category=category)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, category=category, name='BookmarkedSound')

        response = self.client.get(reverse('bookmarks-for-user-for-category',
                                           kwargs={'username': user.username, 'category_id': category.id}))

        self.assertEqual(200, response.status_code)
        self.assertEquals(2, len(response.context['bookmarked_sounds']))
        self.assertContains(response, 'Your bookmarks')
        self.assertContains(response, 'Bookmarks in "Category1"')
        self.assertContains(response, 'Uncategorized</a> (1 bookmark)')
        self.assertContains(response, 'Category1</a> (2 bookmarks)')

    def test_bookmark_category_oldusername(self):
        user = User.objects.get(username='Anton')
        self.client.force_login(user)

        category = bookmarks.models.BookmarkCategory.objects.create(name='Category1', user=user)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11, category=category)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, category=category, name='BookmarkedSound')

        user.username = "new-username"
        user.save()

        response = self.client.get(reverse('bookmarks-for-user-for-category',
                                           kwargs={'username': 'Anton', 'category_id': category.id}))
        # The response is a 301
        self.assertEqual(301, response.status_code)

        # Now follow the redirect
        response = self.client.get(reverse('bookmarks-for-user-for-category',
                                kwargs={'username': 'Anton', 'category_id': category.id}), follow=True)
        # The response is a 200
        self.assertEqual(200, response.status_code)


        self.assertEquals(2, len(response.context['bookmarked_sounds']))
        self.assertContains(response, 'Your bookmarks')
        self.assertContains(response, 'Bookmarks in "Category1"')
        self.assertContains(response, 'Uncategorized</a> (1 bookmark)')
        self.assertContains(response, 'Category1</a> (2 bookmarks)')
