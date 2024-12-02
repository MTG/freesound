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
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from bookmarks.forms import BookmarkForm, BookmarkCategoryForm
from bookmarks.models import Bookmark, BookmarkCategory
from sounds.models import Sound
from utils.downloads import download_sounds
from utils.pagination import paginate
from utils.username import redirect_if_old_username_or_404, raise_404_if_user_is_deleted


@login_required
def bookmarks(request, category_id=None):
    user = request.user
    is_owner = True
    n_uncat = Bookmark.objects.select_related("sound").filter(user=user, category=None).count()
    if not category_id:
        category = None
        bookmarked_sounds = Bookmark.objects.select_related("sound", "sound__user").filter(user=user, category=None)
    else:
        category = get_object_or_404(BookmarkCategory, id=category_id, user=user)
        bookmarked_sounds = category.bookmarks.select_related("sound", "sound__user").all()
    bookmark_categories = BookmarkCategory.objects.filter(user=user).annotate(num_bookmarks=Count('bookmarks'))
    tvars = {'user': user,
             'is_owner': is_owner,
             'n_uncat': n_uncat,
             'category': category,
             'bookmark_categories': bookmark_categories}
    tvars.update(paginate(request, bookmarked_sounds, settings.BOOKMARKS_PER_PAGE))
    return render(request, 'bookmarks/bookmarks.html', tvars)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def bookmarks_for_user(request, username, category_id=None):
    user = request.parameter_user
    is_owner = request.user.is_authenticated and user == request.user
    if is_owner:
        # If accessing own bookmarks using the people/xx/bookmarks URL, redirect to the /home/bookmarks URL
        if category_id:
            return HttpResponseRedirect(reverse('bookmarks-category', args=[category_id]))
        else:
            return HttpResponseRedirect(reverse('bookmarks'))
    else:
        # We only make bookmarks available to bookmark owners (bookmarks are not public)
        raise Http404


@login_required
@transaction.atomic()
def delete_bookmark_category(request, category_id):
    category = get_object_or_404(BookmarkCategory, id=category_id, user=request.user)
    msg = "Removed bookmark category \"" + category.name + "\"."
    category.delete()
    messages.add_message(request, messages.WARNING, msg)
    next = request.GET.get("next", "")
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[request.user.username]))
    
@transaction.atomic()
def download_bookmark_category(request, category_id):
    category = get_object_or_404(BookmarkCategory, id=category_id)
    licenses_url = (reverse('bookmark-category-licenses', args=[category_id]))
    #missing: cache checking done in packdownload
    return download_sounds(licenses_url, category)

def bookmark_category_licenses(category_id):
    category = get_object_or_404(BookmarkCategory, id=category_id)
    attribution = category.get_attribution()
    return HttpResponse(attribution, content_type="text/plain")


@transaction.atomic()
def edit_bookmark_category(request, category_id):

    if not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[request.user.username]))
    
    category = get_object_or_404(BookmarkCategory, id=category_id, user=request.user)

    if request.method == "POST":
        edit_form = BookmarkCategoryForm(request.POST, instance=category)
        print(edit_form.is_bound)
        if edit_form.is_valid():      
            category.name = edit_form.cleaned_data["name"]
            category.save()
            return JsonResponse({"success":True})
        if not edit_form.is_valid():
            print(edit_form.errors.as_json())
    else:
        initial = {"name":category.name}
        edit_form = BookmarkCategoryForm(initial=initial)
    
    tvars = {"category": category,
            "form": edit_form}
    return render(request, 'bookmarks/modal_edit_bookmark_category.html', tvars)
            

    
@login_required
@transaction.atomic()
def add_bookmark(request, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    msg_to_return = ''
    if request.method == 'POST':
        user_bookmark_categories = BookmarkCategory.objects.filter(user=request.user)
        form = BookmarkForm(request.POST,
                         user_bookmark_categories=user_bookmark_categories,
                         sound_id=sound_id,
                         user_saving_bookmark=request.user)
        if form.is_valid():
            saved_bookmark = form.save()
            msg_to_return = f'Bookmark created with name "{saved_bookmark.sound_name}"'
            if saved_bookmark.category:
                msg_to_return += f' under category "{saved_bookmark.category.name}".'
            else:
                msg_to_return += '.'
        else:
            raise Exception()

    if request.is_ajax():
        return JsonResponse({'message': msg_to_return})
    else:
        messages.add_message(request, messages.WARNING, msg_to_return)
        next = request.GET.get("next", "")
        if next:
            return HttpResponseRedirect(next)
        else:
            return HttpResponseRedirect(reverse("sound", args=[sound.user.username, sound.id]))


@login_required
def delete_bookmark(request, bookmark_id):
    bookmark = get_object_or_404(Bookmark, id=bookmark_id, user=request.user)
    msg = "Removed bookmark for sound \"" + bookmark.sound.original_filename + "\"."
    bookmark.delete()
    messages.add_message(request, messages.WARNING, msg)
    next = request.GET.get("next", "")
    page = request.GET.get("page", "1")
    if next:
        return HttpResponseRedirect(next + "?page=" + str(page))
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[request.user.username]) + "?page=" + str(page))


def get_form_for_sound(request, sound_id):
    if not request.user.is_authenticated:
        return render(request, 'bookmarks/modal_bookmark_sound.html', {})

    sound = Sound.objects.get(id=sound_id)
    try:
        last_user_bookmark = \
            Bookmark.objects.filter(user=request.user).order_by('-created')[0]
        # If user has a previous bookmark, use the same category by default (or use none if no category used in last
        # bookmark)
        last_category = last_user_bookmark.category
    except IndexError:
        last_category = None
    user_bookmark_categories = BookmarkCategory.objects.filter(user=request.user)
    form = BookmarkForm(initial={'category': last_category.id if last_category else BookmarkForm.NO_CATEGORY_CHOICE_VALUE},
                     prefix=sound.id,
                     user_bookmark_categories=user_bookmark_categories)
    categories_already_containing_sound = BookmarkCategory.objects.filter(user=request.user,
                                                                          bookmarks__sound=sound).distinct()
    sound_has_bookmark_without_category = Bookmark.objects.filter(user=request.user, sound=sound, category=None).exists()
    add_bookmark_url = '/'.join(
        request.build_absolute_uri(reverse('add-bookmark', args=[sound_id])).split('/')[:-2]) + '/'
    tvars = {
        'bookmarks': Bookmark.objects.filter(user=request.user, sound=sound).exists(),
        'sound_id': sound.id,
        'sound_is_moderated_and_processed_ok': sound.moderated_and_processed_ok,
        'form': form,
        'sound_has_bookmark_without_category': sound_has_bookmark_without_category,
        'categories_aready_containing_sound': categories_already_containing_sound,
        'add_bookmark_url': add_bookmark_url
    }
    return render(request, 'bookmarks/modal_bookmark_sound.html', tvars)
