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

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test.utils import override_settings
from django.urls import reverse
from pytest_django.asserts import assertContains, assertRedirects

import bookmarks.models
from sounds.models import Sound


@pytest.fixture
def bookmark_data(load_fixtures):
    load_fixtures(["licenses", "sounds"])


class TestBookmarks:
    def test_category_licenses_require_owner(self, bookmark_data, client):
        owner = User.objects.get(username="Anton")
        category = bookmarks.models.BookmarkCategory.objects.create(name="Private bookmarks", user=owner)
        bookmarks.models.Bookmark.objects.create(user=owner, sound_id=10, category=category)
        url = reverse("category-licenses", args=[category.id])
        assert client.get(url).status_code == 302
        client.force_login(User.objects.create_user("outsider", email="outsider@example.com"))
        assert client.get(url).status_code == 404
        client.force_login(owner)
        assertContains(client.get(url), category.name)

    @override_settings(ENABLE_COLLECTIONS=False)
    def test_old_bookmarks_for_user_redirect(self, bookmark_data, client):
        user = User.objects.get(username="Anton")
        category = bookmarks.models.BookmarkCategory.objects.create(name="Category1", user=user)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11, category=category)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, category=category)

        # User not logged in, redirect raises 404
        resp = client.get(reverse("bookmarks-for-user", kwargs={"username": "Anton"}))
        assert resp.status_code == 404

        # User logged in, redirect to home/bookmarks page
        client.force_login(user)
        resp = client.get(reverse("bookmarks-for-user", kwargs={"username": "Anton"}))
        assertRedirects(resp, reverse("bookmarks"))

        # User logged in, redirect to home/bookmarks/category page
        resp = client.get(
            reverse("bookmarks-for-user-for-category", kwargs={"username": "Anton", "category_id": category.id})
        )
        assertRedirects(resp, reverse("bookmarks-category", kwargs={"category_id": category.id}))

    @override_settings(ENABLE_COLLECTIONS=False)
    def test_bookmarks(self, bookmark_data, client):
        user = User.objects.get(username="Anton")
        client.force_login(user)

        # Test user has no bookmarks
        response = client.get(reverse("bookmarks"))
        assert response.status_code == 200
        assertContains(response, "There are no uncategorized bookmarks")

        # Create bookmarks
        category = bookmarks.models.BookmarkCategory.objects.create(name="Category1", user=user)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=10)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=11, category=category)
        bookmarks.models.Bookmark.objects.create(user=user, sound_id=12, category=category)

        # Test main bookmarks page
        response = client.get(reverse("bookmarks"))
        assert response.status_code == 200
        assert len(response.context["page"].object_list) == 1  # 1 bookmark uncategorized
        assert len(response.context["bookmark_categories"]) == 1  # 1 bookmark category

        # Test bookmark category page
        response = client.get(reverse("bookmarks-category", kwargs={"category_id": category.id}))
        assert response.status_code == 200
        assert len(response.context["page"].object_list) == 2  # 2 sounds in category
        assertContains(response, category.name)

        # Test category does not exist
        response = client.get(reverse("bookmarks-category", kwargs={"category_id": 1234}))
        assert response.status_code == 404

    def test_cannot_create_duplicate_uncategorized_bookmark(self, bookmark_data):
        user = User.objects.get(username="Anton")
        sound = Sound.objects.first()
        bookmarks.models.Bookmark.objects.create(user=user, sound=sound)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                bookmarks.models.Bookmark.objects.create(user=user, sound=sound)

    def test_delete_category_with_existing_uncategorized_bookmark(self, bookmark_data, client):
        user = User.objects.get(username="Anton")
        sound = Sound.objects.first()
        category = bookmarks.models.BookmarkCategory.objects.create(name="Category1", user=user)
        # Create bookmarks both uncategorized and within the category for the same sound.
        uncategorized = bookmarks.models.Bookmark.objects.create(user=user, sound=sound)
        categorized = bookmarks.models.Bookmark.objects.create(user=user, sound=sound, category=category)

        client.force_login(user)
        response = client.post(reverse("delete-bookmark-category", kwargs={"category_id": category.id}))
        assert response.status_code == 302

        assert not bookmarks.models.BookmarkCategory.objects.filter(id=category.id).exists()
        # the once-categorized bookmark should be deleted but the uncategorized one should remain.
        assert not bookmarks.models.Bookmark.objects.filter(id=categorized.id).exists()
        assert bookmarks.models.Bookmark.objects.filter(id=uncategorized.id).exists()

    def test_delete_category_only_removes_conflicting_bookmarks(self, bookmark_data, client):
        user = User.objects.get(username="Anton")
        sounds = list(Sound.objects.order_by("id")[:2])
        category = bookmarks.models.BookmarkCategory.objects.create(name="Category1", user=user)

        # Existing uncategorized bookmark for first sound.
        conflict_sound_bookmark = bookmarks.models.Bookmark.objects.create(user=user, sound=sounds[0])
        conflicting_categorized = bookmarks.models.Bookmark.objects.create(
            user=user, sound=sounds[0], category=category
        )
        non_conflicting_categorized = bookmarks.models.Bookmark.objects.create(
            user=user, sound=sounds[1], category=category
        )

        client.force_login(user)
        response = client.post(reverse("delete-bookmark-category", kwargs={"category_id": category.id}))
        assert response.status_code == 302

        assert not bookmarks.models.BookmarkCategory.objects.filter(id=category.id).exists()
        # Only the conflicting bookmark is deleted.
        assert not bookmarks.models.Bookmark.objects.filter(id=conflicting_categorized.id).exists()
        assert bookmarks.models.Bookmark.objects.filter(id=conflict_sound_bookmark.id).exists()
        non_conflict = bookmarks.models.Bookmark.objects.get(id=non_conflicting_categorized.id)
        assert non_conflict.category is None
