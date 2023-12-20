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
from django.db import models

from sounds.models import Sound


class BookmarkCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default="")

    def __str__(self):
        return f"{self.name}"


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(
        BookmarkCategory, blank=True, null=True, default=None, related_name='bookmarks', on_delete=models.SET_NULL
    )
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __str__(self):
        return f"Bookmark: {self.name}"

    @property
    def category_name_or_uncategorized(self):
        if self.category is None:
            return 'Uncategorized'
        else:
            return self.category.name

    @property
    def sound_name(self):
        return self.sound.original_filename

    class Meta:
        ordering = ("-created",)
        unique_together = (('user_id', 'category_id', 'sound_id'),)
