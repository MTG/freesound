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

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from fscollections.models import Collection
from sounds.models import Sound

@login_required
def collections(request, collection_id=None):
    user = request.user
    user_collections = Collection.objects.filter(author=user).order_by('-created') #first user collection should be on top - this would affect the if block
    #if no collection id is provided for this URL, render the oldest collection in the webpage
    if not collection_id:
        collection = user_collections.last()    
    else:
        collection = get_object_or_404(Collection, id=collection_id)
    
    tvars = {'collection': collection,
             'collections_for_user': user_collections}
    
    return render(request, 'collections/collections.html', tvars)

#upon creating a new user, create alongside a personal PRIVATE collection to store sounds

def add_sound_to_collection(request, sound_id, collection_id):
    sound = get_object_or_404(Sound, id=sound_id)
    collection = get_object_or_404(Collection, id=collection_id, author=request.user)
    
    if sound.moderation_state=='OK':
        collection.sounds.add(sound) 
        collection.save()
        return True
    else:
        return "sound not moderated or not collection owner"

def delete_sound_from_collection(request, sound_id, collection_id):
    sound = get_object_or_404(Sound, id=sound_id)
    collection = get_object_or_404(Collection, id=collection_id, author=request.user)

    if sound in collection.sound.all():
        collection.sounds.remove(sound)
        collection.save()
        return True
    else:
        return "this sound is not in the collection"