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
from django.utils.text import slugify

from sounds.models import Sound, License
from django.template.loader import render_to_string


class BookmarkCategory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default="")
    
    def __str__(self):
        return f"{self.name}"
    
    def get_attribution(self, sound_qs=None):
        #If no queryset of sounds is provided, take it from the bookmark category
        if sound_qs is None:
            bookmarked_sounds = Bookmark.objects.filter(category_id=self.id).values("sound_id")
            sound_qs = Sound.objects.filter(id__in=bookmarked_sounds, processing_state="OK", moderation_state="OK").select_related('user','license')
        
        users = User.objects.filter(sounds__in=sound_qs).distinct()
        # Generate text file with license info
        licenses = License.objects.filter(sound__id__in=sound_qs).distinct()
        attribution = render_to_string(("sounds/multiple_sounds_attribution.txt"),
            dict(type="Bookmark Category",
                users=users,
                object=self,
                licenses=licenses,
                sound_list=sound_qs))
        return attribution
    
    @property
    def download_filename(self):
        name_slug = slugify(self.name)
        username_slug = slugify(self.user.username)
        return "%d__%s__%s.zip" % (self.id, username_slug, name_slug)


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(
        BookmarkCategory, blank=True, null=True, default=None, related_name='bookmarks', on_delete=models.SET_NULL)
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    
    def __str__(self):
        return f"Bookmark: {self.sound} by {self.user}"

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
        ordering = ("-created", )
        unique_together = (('user_id', 'category_id', 'sound_id'),)
