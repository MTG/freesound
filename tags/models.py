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
from django.urls import reverse
from django.utils.encoding import smart_str


class Tag(models.Model):
    name = models.SlugField(unique=True, db_index=True, max_length=100)

    def __str__(self):
        return self.name

    def get_browse_tag_url(self):
        return reverse("tags", self.name)

    class Meta:
        ordering = ("name",)


class SoundTag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    sound = models.ForeignKey("sounds.Sound", on_delete=models.CASCADE)

    created = models.DateTimeField(db_index=True, auto_now_add=True)

    def __str__(self):
        return f"{self.user} tagged {self.sound} - {self.tag}"

    def get_absolute_url(self):
        return reverse("tag", args=[smart_str(self.tag.id)])

    class Meta:
        ordering = ("-created",)
        unique_together = (("tag", "sound_id"),)


# Class to get old tags ids linked to new tag ids
# The goal is to at some point deprecate the old tag ids completely
class FS1Tag(models.Model):
    # The old id from FS1
    fs1_id = models.IntegerField(unique=True, db_index=True)

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
