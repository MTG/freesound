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
from fscollections.forms import CollectionSoundForm
from sounds.models import Sound
from sounds.views import add_sounds_modal_helper

@login_required
def collections(request, collection_id=None):
    user = request.user
    user_collections = Collection.objects.filter(author=user).order_by('-created') #first user collection should be on top - this would affect the if block
    is_owner = False
    #if no collection id is provided for this URL, render the oldest collection in the webpage
    #be careful when loading this url without having any collection for a user
    #rn the relation user-collection only exists when you own the collection

    if not collection_id:
        collection = user_collections.last()    
    else:
        collection = get_object_or_404(Collection, id=collection_id)

    if user == collection.author:
        is_owner = True

    tvars = {'collection': collection,
             'collections_for_user': user_collections,
             'is_owner': is_owner}
    
    return render(request, 'collections/collections.html', tvars)

#NOTE: tbd - when a user wants to save a sound without having any collection, create a personal bookmarks collection

def add_sound_to_collection(request, sound_id, collection_id=None):
    sound = get_object_or_404(Sound, id=sound_id)
    if collection_id is None:
        collection = Collection.objects.filter(author=request.user).order_by("created")[0]
    else:    
        collection = get_object_or_404(Collection, id=collection_id, author=request.user)
    
    if sound.moderation_state=='OK':
        collection.sounds.add(sound) 
        collection.save()
        return HttpResponseRedirect(reverse("collections", args=[collection.id]))
    else:
        return "sound not moderated or not collection owner"
    

def delete_sound_from_collection(request, collection_id, sound_id):
    #this should work as in Packs - select several sounds and remove them all at once from the collection
    #by now it works as in Bookmarks in terms of UI
    sound = get_object_or_404(Sound, id=sound_id)
    collection = get_object_or_404(Collection, id=collection_id, author=request.user)
    collection.sounds.remove(sound)
    collection.save()
    return HttpResponseRedirect(reverse("collections", args=[collection.id]))

@login_required
def get_form_for_collecting_sound(request, sound_id):
    user = request.user
    sound = Sound.objects.get(id=sound_id)
    
    try:
        last_collection = \
            Collection.objects.filter(author=request.user).order_by('-created')[0]
        # If user has a previous bookmark, use the same category by default (or use none if no category used in last
        # bookmark)
    except IndexError:
        last_collection = None
    
    user_collections = Collection.objects.filter(author=user).order_by('-created')
    form = CollectionSoundForm(initial={'collection': last_collection.id if last_collection else CollectionSoundForm.NO_COLLECTION_CHOICE_VALUE},
                               prefix=sound.id,
                               user_collections=user_collections)
    
    collections_already_containing_sound = Collection.objects.filter(author=user, collection__sounds=sound).distinct()
    tvars = {'user': user,
             'sound': sound,
             'last_collection': last_collection,
             'collections': user_collections,
             'form': form,
             'collections_with_sound': collections_already_containing_sound}
    print("NICE CHECKPOINT")
    print(tvars)
    
    return render(request, 'modal_collect_sound.html', tvars)


#NOTE: there should be two methods to add a sound into a collection
#1: adding from the sound.html page through a "bookmark-like" button and opening a Collections modal
#2: from the collection.html page through a search-engine modal as done in Packs
"""
@login_required
def add_sounds_modal_for_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    tvars = add_sounds_modal_helper(request, username=collection.author.username)
    tvars.update({
        'modal_title': 'Add sounds to Collection',
        'help_text': 'Collections are great!',
    })
    return render(request, 'sounds/modal_add_sounds.html', tvars)
"""