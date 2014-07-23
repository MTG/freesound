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

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from sounds.models import Sound
from bookmarks.models import *
from bookmarks.forms import BookmarkCategoryForm, BookmarkForm
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from datetime import datetime
from django.contrib import messages
from utils.pagination import paginate
from utils.functional import combine_dicts
from django.http import HttpResponse
import json

def bookmarks(request, username, category_id = None):
    
    user = get_object_or_404(User, username__iexact=username)
    is_owner = request.user.is_authenticated and user == request.user
    
    '''
    if is_owner and request.POST and "create_cat" in request.POST:
        form_bookmark_category = BookmarkCategoryForm(request.POST, instance=BookmarkCategory(user=user))
        if form_bookmark_category.is_valid():
            form_bookmark_category.save()
        
        form_bookmark_category = BookmarkCategoryForm()
        
    form_bookmark_category = BookmarkCategoryForm()
    '''    
    
    n_uncat = Bookmark.objects.select_related("sound").filter(user=user,category=None).count()
    
    if not category_id:
        bookmarked_sounds = Bookmark.objects.select_related("sound").filter(user=user,category=None)
    else:
        category = get_object_or_404(BookmarkCategory,id=category_id,user=user)
        bookmarked_sounds = category.bookmarks.select_related("sound").all()
    
    bookmark_categories = BookmarkCategory.objects.filter(user=user)
    
    return render_to_response('bookmarks/bookmarks.html', combine_dicts(locals(),paginate(request, bookmarked_sounds, 30)), context_instance=RequestContext(request))

@login_required
def delete_bookmark_category(request, category_id):
    
    category = get_object_or_404(BookmarkCategory,id=category_id, user=request.user)
    msg = "Deleted bookmark category \"" + category.name + "\"."
    category.delete()
    messages.add_message(request, messages.WARNING, msg)
    
    next = request.GET.get("next","")
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[request.user.username]))

@login_required
def add_bookmark(request, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)

    if request.POST:
        form = BookmarkForm(request.POST, instance=Bookmark(user=request.user, sound=sound))
        form.fields['category'].queryset = BookmarkCategory.objects.filter(user=request.user)
        if form.is_valid():
            form.save()

    if request.is_ajax():
        return HttpResponse()

    else:
        msg = "Added new bookmark for sound \"" + sound.original_filename + "\"."
        messages.add_message(request, messages.WARNING, msg)
        
        next = request.GET.get("next","")
        if next:
            return HttpResponseRedirect(next)
        else:
            return HttpResponseRedirect(reverse("sound", args=[sound.user.username, sound.id]))


@login_required
def delete_bookmark(request, bookmark_id):
    
    bookmark = get_object_or_404(Bookmark,id=bookmark_id, user=request.user)
    msg = "Deleted bookmark for sound \"" + bookmark.sound.original_filename + "\"."
    bookmark.delete()
    messages.add_message(request, messages.WARNING, msg)
    
    next = request.GET.get("next","")
    page = request.GET.get("page", "1")
    if next:
        return HttpResponseRedirect(next + "?page=" + str(page))
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[request.user.username]) + "?page=" + str(page))

@login_required       
def get_form_for_sound(request, sound_id):
    sound = Sound.objects.get(id=sound_id)
    form = BookmarkForm(instance = Bookmark(name=sound.original_filename), prefix = sound.id)
    form.fields['category'].queryset = BookmarkCategory.objects.filter(user=request.user)
    categories_already_containing_sound = BookmarkCategory.objects.filter(user=request.user, bookmarks__sound=sound).distinct()
    add_bookmark_url = '/'.join(reverse('add-bookmark', args=[sound_id]).split('/')[:-2]) + '/'
    add_bookmark_url = '/'.join(request.build_absolute_uri(reverse('add-bookmark', args=[sound_id])).split('/')[:-2]) + '/'

    data_dict = {
        'bookmarks': Bookmark.objects.filter(user=request.user,sound=sound).count() != 0,
        'sound_id':sound.id,
        'form':form,
        'categories_aready_containing_sound':categories_already_containing_sound,
        'add_bookmark_url': add_bookmark_url
    }
    template = 'bookmarks/bookmark_form.html'
    return render_to_response(template, data_dict, context_instance = RequestContext(request))
