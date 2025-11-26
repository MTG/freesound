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

import logging

from django.contrib.auth.models import User

from bookmarks.models import Bookmark, BookmarkCategory
from fscollections.models import Collection, CollectionSound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = (
        "Transform all existing bookmarks of all users into collections. This will not remove bookmark objects. Bookmarks categories will be turned"
        ' into collections. Bookmarks without category will be put into a collection named "My bookmarks".'
    )

    def handle(self, *args, **options):
        self.log_start()

        # Create collections from bookmark categories
        num_bookmark_collections = BookmarkCategory.objects.count()
        n_collections_created = 0
        for count, bookmark_category in enumerate(BookmarkCategory.objects.all()):
            user = bookmark_category.user
            collection_name = bookmark_category.name
            bookmark_category_sounds = Bookmark.objects.filter(user=user, category=bookmark_category)
            if bookmark_category_sounds.exists():
                collection, created = Collection.objects.get_or_create(user=user, name=collection_name, public=False)
                if created:
                    for bookmark in bookmark_category_sounds:
                        CollectionSound.objects.create(
                            collection=collection, sound=bookmark.sound, status="OK", user=collection.user
                        )
                    # No need to manually set num_sounds as it is set on save()
                    collection.save()
                    n_collections_created += 1

            if count % 100 == 0:
                console_logger.info(f"Processed {count + 1} out of {num_bookmark_collections} bookmark categories.")

        # Now create default "My bookmarks" collection for users that have bookmarks without category
        bookmarks_without_category_uids = (
            Bookmark.objects.filter(category__isnull=True).values_list("user_id", flat=True).distinct()
        )
        num_bookmarks_without_category_uids = len(bookmarks_without_category_uids)
        for count, uid in enumerate(bookmarks_without_category_uids):
            user = User.objects.get(id=uid)
            collection_name = "My bookmarks"
            bookmark_category_sounds = Bookmark.objects.filter(user=user, category__isnull=True)
            if bookmark_category_sounds.exists():
                collection, created = Collection.objects.get_or_create(
                    user=user, name=collection_name, is_default_collection=True, public=False
                )
                if created:
                    for bookmark in bookmark_category_sounds:
                        CollectionSound.objects.create(
                            collection=collection, sound=bookmark.sound, status="OK", user=collection.user
                        )
                    # No need to manually set num_sounds as it is set on save()
                    collection.save()
                    n_collections_created += 1

            if count % 100 == 0:
                console_logger.info(
                    f"Processed {count + 1} out of {num_bookmarks_without_category_uids} users with uncategorized bookmarks."
                )

        self.log_end({"n_collections_created": n_collections_created})
