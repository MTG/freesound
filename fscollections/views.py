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

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from fscollections.models import Collection, CollectionSound
from fscollections.forms import CollectionSoundForm
from sounds.models import Sound
from sounds.views import add_sounds_modal_helper
from utils.pagination import paginate


@login_required
def collections_for_user(request, collection_id=None):
    user = request.user
    user_collections = Collection.objects.filter(user=user).order_by('-created') 
    is_owner = False
    #if no collection id is provided for this URL, render the oldest collection
    #be careful when loading this url without having any collection for a user
    #only show the collections for which you're the user(owner)
    
    if not collection_id:
        collection = user_collections.last()    
    else:
        collection = get_object_or_404(Collection, id=collection_id)

    if user == collection.user:
        is_owner = True


    tvars = {'collection': collection,
             'collections_for_user': user_collections,
             'is_owner': is_owner}
    
    collection_sounds = CollectionSound.objects.filter(collection=collection)
    paginator = paginate(request, collection_sounds, settings.BOOKMARKS_PER_PAGE)
    page_sounds = Sound.objects.ordered_ids([col_sound.sound_id for col_sound in paginator['page'].object_list])
    tvars.update(paginator)
    tvars['page_collection_and_sound_objects'] = zip(paginator['page'].object_list, page_sounds)
    return render(request, 'collections/collections.html', tvars)

#NOTE: tbd - when a user wants to save a sound without having any collection, create a personal bookmarks collection

def add_sound_to_collection(request, sound_id):
    #this view from now on should create a new CollectionSound object instead of adding
    #a sound to collection.sounds
    # TODO: add restrictions for sound repetition and for user being owner/maintainer
    sound = get_object_or_404(Sound, id=sound_id)
    msg_to_return = ''

    if not request.GET.get('ajax'):
        HttpResponseRedirect(reverse("sound", args=[sound.user.username,sound.id]))

    if request.method == 'POST':
        #by now work with direct additions (only user-wise, not maintainer-wise)
        user_collections = Collection.objects.filter(user=request.user)
        form = CollectionSoundForm(request.POST, sound_id=sound_id, user_collections=user_collections, user_saving_sound=request.user)

        if form.is_valid():
            saved_collection = form.save()
            # TODO: moderation of CollectionSounds to be accounted for users who are neither maintainers nor owners
            CollectionSound(user=request.user, collection=saved_collection, sound=sound, status="OK").save()
            saved_collection.num_sounds =+ 1 #this should be done with a signal/method in Collection models
            saved_collection.save()
            msg_to_return = f'Sound "{sound.original_filename}" saved under collection {saved_collection.name}'
            return JsonResponse('message', msg_to_return)
        else:
            msg_to_return = 'This sound already exists in this category'
            return JsonResponse('message', msg_to_return)
        

def delete_sound_from_collection(request, collectionsound_id):
    #this should work as in Packs - select several sounds and remove them all at once from the collection
    #by now it works as in Bookmarks in terms of UI
    #TODO: this should be done through a POST request method, would be easier to send CollectionSound ID and delete it directly
    # this would save up a query
    collection_sound = get_object_or_404(CollectionSound, id=collectionsound_id)
    collection = collection_sound.collection
    collection_sound.delete()
    return HttpResponseRedirect(reverse("collections", args=[collection.id]))

@login_required
def get_form_for_collecting_sound(request, sound_id):

    sound = Sound.objects.get(id=sound_id)
    
    try:
        last_collection = \
            Collection.objects.filter(user=request.user).order_by('-created')[0]
        # If user has a previous bookmark, use the same category by default (or use none if no category used in last
        # bookmark)
    except IndexError:
        last_collection = None
    
    user_collections = Collection.objects.filter(user=request.user).order_by('-created')
    form = CollectionSoundForm(initial={'collection': last_collection.id if last_collection else CollectionSoundForm.NO_COLLECTION_CHOICE_VALUE},
                               sound_id=sound.id,
                               prefix=sound.id,
                               user_collections=user_collections)
    
    collections_already_containing_sound = Collection.objects.filter(user=request.user, collectionsound__sound__id=sound.id).distinct()
    # collect_sound_url = '/'.join(
       # request.build_absolute_uri(reverse('add-sound-to-collection', args=[sound_id])).split('/')[:-2]) + '/'
    tvars = {'user': request.user,
             'sound': sound,
             'sound_is_moderated_and_processed_ok': sound.moderated_and_processed_ok,
             'last_collection': last_collection,
             'collections': user_collections,
             'form': form,
             'collections_with_sound': collections_already_containing_sound
             }
    
    return render(request, 'collections/modal_collect_sound.html', tvars)


#NOTE: there should be two methods to add a sound into a collection
#1: adding from the sound.html page through a "bookmark-like" button and opening a Collections modal
#2: from the collection.html page through a search-engine modal as done in Packs
"""
@login_required
def add_sounds_modal_for_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    tvars = add_sounds_modal_helper(request, username=collection.user.username)
    tvars.update({
        'modal_title': 'Add sounds to Collection',
        'help_text': 'Collections are great!',
    })
    return render(request, 'sounds/modal_add_sounds.html', tvars)
"""