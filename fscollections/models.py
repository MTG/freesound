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

from sounds.models import Sound, License

class Collection(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    name = models.CharField(max_length=255) #max_length as in Packs (128 for Bookmarks)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    modified = models.DateTimeField(db_index=True, auto_now=True)
    # NOTE: double-check if description should be required (and how to display it)
    description = models.TextField(blank=True)
    maintainers = models.ManyToManyField(User, related_name="collection_maintainer", blank=True)
    num_sounds = models.PositiveIntegerField(default=0)
    public = models.BooleanField(default=False)
    is_default_collection = models.BooleanField(default=False)
    #NOTE: Don't fear migrations, you're just testing
    #sounds are related to collections through CollectionSound model (bookmark-wise)
    #contributors = delicate stuff 
    #subcolletion_path = sth with tagn and routing folders for downloads
    #follow relation for users and collections (intersted but not owner nor contributor)

    def __str__(self):
        return f"{self.name}"


class CollectionSound(models.Model):
   #this model relates collections and sounds
   #it might be worth adding a name field composed of the sound ID and the collection name for
   # for the sake of queries understanding
   user = models.ForeignKey(User, on_delete=models.CASCADE) 
   sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
   collection = models.ForeignKey(Collection, related_name='collectionsound', on_delete=models.CASCADE)
   created = models.DateTimeField(db_index=True, auto_now_add=True)
   
   STATUS_CHOICES = (
        ("PE", 'Pending'),
        ("OK", 'Accepted'),
        ("RE", 'Refused'),
    )
   status = models.CharField(db_index=True, max_length=2, choices=STATUS_CHOICES, default="PE")
   #sound won't be added to collection until maintainers approve the sound