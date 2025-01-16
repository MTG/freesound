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

    author = models.ForeignKey(User, on_delete=models.CASCADE) 
    name = models.CharField(max_length=128, default="BookmarkCollection") #add restrictions
    sounds = models.ManyToManyField(Sound, related_name="collections") 
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    description = models.TextField(max_length=500, default="")
    #NOTE: before next migration add a num_sounds attribute
    #bookmarks = True or False depending on it being the BookmarkCollection for a user (the one created for the first sound without collection assigned)
    #contributors = delicate stuff
    #subcolletion_path = sth with tagsn and routing folders for downloads
    #follow relation for users and collections (intersted but not owner nor contributor)
    #sooner or later you'll need to start using forms for adding sounds to collections xd


    def __str__(self):
        return f"{self.name}"

'''    
class CollectionSound(models.Model):
   ''' 