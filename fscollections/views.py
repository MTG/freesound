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
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from fscollections.models import Collection, CollectionSound
from fscollections.forms import CollectionSoundForm, CollectionEditForm, MaintainerForm, CreateCollectionForm
from sounds.models import Sound
from sounds.views import add_sounds_modal_helper
from utils.pagination import paginate
from utils.downloads import download_sounds


@login_required
def collection(request, collection_id):
    user = request.user
    is_owner = False
    is_maintainer = False
    maintainers = []
    # if no collection id is provided for this URL, render the oldest collection
    # only show the collections for which you're the user(owner)
    if not collection_id:
        # this could probably be a JsonResponse message indicating an error
        return HttpResponseRedirect(reverse('your-collections'))
    else:
        collection = get_object_or_404(Collection, id=collection_id)
    
    maintainers = User.objects.filter(collection_maintainer=collection.id)
    if user == collection.user:
        is_owner = True
    elif user in maintainers:
        is_maintainer = True

    tvars = {'collection': collection,
             'is_owner': is_owner,
             'is_maintainer': is_maintainer,
             'maintainers': maintainers}
    # one URL needed to display all collections and one URL to display ONE collection at a time
    # the collections_for_user can be reused to display ONE collection so give it a thought on full collections display
    collection_sounds = CollectionSound.objects.filter(collection=collection).order_by('created')
    paginator = paginate(request, collection_sounds, settings.BOOKMARKS_PER_PAGE)
    page_sounds = Sound.objects.ordered_ids([col_sound.sound_id for col_sound in paginator['page'].object_list])
    tvars.update(paginator)
    tvars['page_collection_and_sound_objects'] = zip(paginator['page'].object_list, page_sounds)
    return render(request, 'collections/collection.html', tvars)

@login_required
def collections_for_user(request):
    user = request.user
    user_collections = Collection.objects.filter(user=user).order_by('-modified')
    maintainer_collections = Collection.objects.filter(maintainers__id=user.id).order_by('-modified')
    tvars = {'user_collections': user_collections,
             'maintainer_collections': maintainer_collections
             }
    # one URL needed to display all collections and one URL to display ONE collection at a time
    # the collections_for_user can be reused to display ONE collection so give it a thought on full collections display
    return render(request, 'collections/your_collections.html', tvars)


def add_sound_to_collection(request, sound_id):
    # TODO: add restrictions for sound repetition and for user being owner/maintainer
    # this does not work when adding sounds from search results
    sound = get_object_or_404(Sound, id=sound_id)
    msg_to_return = ''

    if not request.GET.get('ajax'):
        HttpResponseRedirect(reverse("sound", args=[sound.user.username,sound.id]))

    if request.method == 'POST':
        user_collections = Collection.objects.filter(user=request.user) | Collection.objects.filter(maintainers__id=request.user.id)
        user_collections = user_collections.distinct().order_by('modified')
        form = CollectionSoundForm(request.POST, sound_id=sound_id, user_collections=user_collections, user_saving_sound=request.user)
    
        if form.is_valid():
            saved_collection = form.save()
            # TODO: moderation of CollectionSounds to be accounted for users who are neither maintainers nor owners
            CollectionSound(user=request.user, collection=saved_collection, sound=sound, status="OK").save()
            saved_collection.num_sounds += 1 #this should be done with a signal/method in Collection models
            saved_collection.save()
            msg_to_return = f'Sound "{sound.original_filename}" saved under collection {saved_collection.name}'
            return JsonResponse({'success': True, 'message': msg_to_return})

def delete_sound_from_collection(request, collectionsound_id):
    collection_sound = get_object_or_404(CollectionSound, id=collectionsound_id)
    collection = collection_sound.collection
    if request.method=="POST":
        collection_maintainers = User.objects.filter(collection_maintainer=collection.id)
        if request.user != collection.user and request.user not in collection_maintainers:
            return HttpResponseRedirect(reverse("collection", args=[collection.id]))
        else:
            collection_sound.delete()
            collection.num_sounds -= 1 #this shouldn't be done like this but it is for the sake of tests
            collection.save()
            return HttpResponseRedirect(reverse("collection", args=[collection.id]))

@login_required
def get_form_for_collecting_sound(request, sound_id):

    sound = Sound.objects.get(id=sound_id)
    
    try:
        last_collection = \
            Collection.objects.filter(user=request.user).order_by('-modified')[0]
        # If user has a previous bookmark, use the same category by default (or use none if no category used in last
        # bookmark)
    except IndexError:
        last_collection = None
    
    user_collections = Collection.objects.filter(user=request.user) | Collection.objects.filter(maintainers__id=request.user.id)
    user_collections = user_collections.distinct().order_by('modified')
    form = CollectionSoundForm(initial={'collection': last_collection.id if last_collection else CollectionSoundForm.BOOKMARK_COLLECTION_CHOICE_VALUE},
                               sound_id=sound.id,
                               prefix=sound.id,
                               user_collections=user_collections,
                               user_saving_sound=request.user)
    collections_already_containing_sound = Collection.objects.filter(user=request.user, collectionsound__sound__id=sound.id).distinct()
    tvars = {'user': request.user,
             'sound': sound,
             'sound_is_moderated_and_processed_ok': sound.moderated_and_processed_ok,
             'last_collection': last_collection,
             'collections': user_collections,
             'form': form,
             'collections_with_sound': collections_already_containing_sound
             }
    
    return render(request, 'collections/modal_collect_sound.html', tvars)

def create_collection(request):
    if not request.GET.get('ajax'):
      return HttpResponseRedirect(reverse("collections"))
    if request.method == "POST":
        form = CreateCollectionForm(request.POST, user=request.user)
        if form.is_valid():
            Collection(user = request.user, 
                    name = form.cleaned_data['name'], 
                    description = form.cleaned_data['description']).save()
            return JsonResponse({'success': True})
    else:
        form = CreateCollectionForm(user=request.user)
    tvars = {'form': form}
    return render(request, 'collections/modal_create_collection.html', tvars)
    
def delete_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)

    if request.user==collection.user:
        collection.delete()
        return HttpResponseRedirect(reverse('your-collections'))
    else:
        return HttpResponseRedirect(reverse('edit-collection', args=[collection.id]))

def edit_collection(request, collection_id):
    
    collection = get_object_or_404(Collection, id=collection_id)
    collection_sounds = ",".join([str(s.id) for s in Sound.objects.filter(collectionsound__collection=collection)])
    collection_maintainers = ",".join([str(u.id) for u in User.objects.filter(collection_maintainer=collection.id)])

    if request.user == collection.user:
        is_owner = True
    else:
        is_owner = False
    if str(request.user.id) in collection_maintainers:
        is_maintainer = True
    else:
        is_maintainer = False
    
    current_sounds = list()
    if request.method=="POST":
        form = CollectionEditForm(request.POST, instance=collection, label_suffix='', is_owner=is_owner, is_maintainer=is_maintainer)
        if form.is_valid():
            form.save(user_adding_sound=request.user)
            return HttpResponseRedirect(reverse('collection', args=[collection.id]))
        
    else:
        form = CollectionEditForm(instance=collection, initial=dict(collection_sounds=collection_sounds, collection_maintainers=collection_maintainers), label_suffix='', is_owner=is_owner)
        current_sounds = Sound.objects.bulk_sounds_for_collection(collection_id=collection.id)
        current_maintainers = User.objects.filter(collection_maintainer=collection.id)
        form.collection_sound_objects = current_sounds
        form.collection_maintainers_objects = current_maintainers
        display_fields = ["name", "description", "public"]

    tvars = {
        "form": form,
        "collection": collection,
        "is_owner": is_owner,
        "is_maintainer": is_maintainer,
        "display_fields": display_fields,
    }
    
    return render(request, 'collections/edit_collection.html', tvars)

def download_collection(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    collection_sounds = CollectionSound.objects.filter(collection=collection).values('sound_id')
    sounds_list = Sound.objects.filter(id__in=collection_sounds, processing_state="OK", moderation_state="OK").select_related('user','license')
    licenses_url = (reverse('collection-licenses', args=[collection_id]))
    licenses_content = collection.get_attribution(sound_qs=sounds_list)
    collection.num_downloads += 1
    return download_sounds(licenses_url, licenses_content, sounds_list, collection.download_filename)

def collection_licenses(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    attribution = collection.get_attribution()
    return HttpResponse(attribution, content_type="text/plain")

def add_sounds_modal_for_collection_edit(request):
    tvars = add_sounds_modal_helper(request)
    tvars.update({
        'modal_title':'Add sounds to collection',
        'help_text':'Modal to add sounds to your collection'})
    return render(request, 'sounds/modal_add_sounds.html', tvars)
    
def add_maintainer_modal(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    form = MaintainerForm()
    # TODO: the below statements exclude users with whitespaces in their usernames (and they still exist)
    usernames = request.GET.get('q','').replace(' ','').split(',')
    excluded_users = request.GET.get('exclude','').split(',')

    # if request.GET.get('ajax'):
      #  new_maintainers = User.objects.filter(username__in=usernames)
    # TODO: the above conditional is more suitable for its purpose (first modal load)
    # However, there's a strange error in collections.js, when loading the object selector that contains the maintainers.
    # The selectedIds and unselectedIds parameters are not added to its dataset until the user interacts with a checkbox.
    # Until that's not solved, the below if statement must be used to avoid crashings
    if excluded_users[0] == '':
        new_maintainers = User.objects.filter(username__in=usernames)
    else:
        new_maintainers = User.objects.filter(username__in=usernames).exclude(id__in=excluded_users)
    
    tvars = ({'collection': collection,
             'help_text': 'Modal to add maintainers to your collection',
             'form': form,
             'new_maintainers': new_maintainers})
    
    return render(request, 'collections/modal_add_maintainer.html', tvars)