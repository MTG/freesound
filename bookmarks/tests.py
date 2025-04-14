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
from django.test import TestCase, override_settings
from django.urls import reverse

import bookmarks.models


class BookmarksTest(TestCase):

    fixtures = ['licenses', 'sounds']

    def test_old_bookmarks_for_user_redirect(self):
        user = User.objects.get(username='Anton')
        category = bookmarks.models.BookmarkCategory.objects.create(name='Category1', user=user)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11, category=category)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, category=category)

        # User not logged in, redirect raises 404
        resp = self.client.get(reverse('bookmarks-for-user', kwargs={'username': 'Anton'}))
        self.assertEqual(404, resp.status_code)
    
        # User logged in, redirect to home/bookmarks page
        self.client.force_login(user)
        resp = self.client.get(reverse('bookmarks-for-user', kwargs={'username': 'Anton'}))
        self.assertRedirects(resp, reverse('bookmarks'))

        # User logged in, redirect to home/bookmarks/category page
        resp = self.client.get(reverse('bookmarks-for-user-for-category', kwargs={'username': 'Anton', 'category_id': category.id}))
        self.assertRedirects(resp, reverse('bookmarks-category', kwargs={'category_id': category.id}))
           
    def test_bookmarks(self):
        user = User.objects.get(username='Anton')
        self.client.force_login(user)

        # Test user has no bookmarks
        response = self.client.get(reverse('bookmarks'))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'There are no uncategorized bookmarks')
        
        # Create bookmarks
        category = bookmarks.models.BookmarkCategory.objects.create(name='Category1', user=user)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11, category=category)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, category=category)

        # Test main bookmarks page
        response = self.client.get(reverse('bookmarks'))
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.context['page'].object_list))  # 1 bookmark uncategorized
        self.assertEqual(1, len(response.context['bookmark_categories']))  # 1 bookmark category

        # Test bookmark category page
        response = self.client.get(reverse('bookmarks-category', kwargs={'category_id': category.id}))
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.context['page'].object_list))  # 2 sounds in category
        self.assertContains(response, category.name)

        # Test category does not exist
        response = self.client.get(reverse('bookmarks-category', kwargs={'category_id': 1234}))
        self.assertEqual(404, response.status_code)
