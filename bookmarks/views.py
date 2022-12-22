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

from builtins import str
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from bookmarks.forms import BookmarkForm, BwBookmarkForm
from bookmarks.models import Bookmark, BookmarkCategory
from sounds.models import Sound
from utils.frontend_handling import using_beastwhoosh, render
from utils.pagination import paginate
from utils.username import redirect_if_old_username_or_404, raise_404_if_user_is_deleted


@login_required
def bookmarks(request, category_id=None):
    user = request.user
    is_owner = True
    return bookmarks_view_helper(request, user, is_owner, category_id)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def bookmarks_for_user(request, username, category_id=None):
    user = request.parameter_user
    is_owner = request.user.is_authenticated and user == request.user
    if not settings.BW_BOOKMARK_PAGES_PUBLIC and not is_owner:
        # In BW we only make bookmarks available to bookmark owners (bookmarks are not public)
        # When fully moved to BW, then we can add @login_required and use only the url pattern under /home for bookmarks
        raise Http404
    if using_beastwhoosh(request) and is_owner:
        # If accesing own bookmarks using the poeple/xx/bookmarks URL, redirect to the /home/bookmarks URL
        return HttpResponseRedirect(reverse('bookmarks'))
    return bookmarks_view_helper(request, user, is_owner, category_id)


def bookmarks_view_helper(request, user, is_owner, category_id):
    # NOTE: we use this helper for the bookmarks and bookmarks_for_user views so the code is reused. When fully switching to BW,
    # the bookmarks_for_user view could be remove as bookmarks won't be public anymore
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
    tvars.update(paginate(request, bookmarked_sounds, settings.BOOKMARKS_PER_PAGE if not using_beastwhoosh(request) else settings.BOOKMARKS_PER_PAGE_BW))
    return render(request, 'bookmarks/bookmarks.html', tvars)


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


@login_required
@transaction.atomic()
def add_bookmark(request, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    msg_to_return = ''
    if request.method == 'POST':
        FormToUse = BwBookmarkForm if using_beastwhoosh(request) else BookmarkForm
        form = FormToUse(request.POST, instance=Bookmark(user=request.user, sound=sound))
        form.fields['category'].queryset = BookmarkCategory.objects.filter(user=request.user)
        if form.is_valid():
            saved_bookmark = form.save()
            msg_to_return = u'Bookmark created with name "{}"'.format(saved_bookmark.name_or_sound_name)
            if saved_bookmark.category:
                msg_to_return += u' under category "{}".'.format(saved_bookmark.category.name)
            else:
                msg_to_return += '.'

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


@login_required
def get_form_for_sound(request, sound_id):
    sound = Sound.objects.get(id=sound_id)
    FormToUse = BwBookmarkForm if using_beastwhoosh(request) else BookmarkForm
    try:
        last_user_bookmark = \
            Bookmark.objects.filter(user=request.user).order_by('-created')[0]
        # If user has a previous bookmark, use the same category by default (or use none if no category used in last
        # bookmark)
        last_category = last_user_bookmark.category
    except IndexError:
        last_category = None
    form = FormToUse(instance=Bookmark(name=sound.original_filename),
                     initial={'category': last_category}, prefix=sound.id)
    form.fields['category'].queryset = BookmarkCategory.objects.filter(user=request.user)
    categories_already_containing_sound = BookmarkCategory.objects.filter(user=request.user,
                                                                          bookmarks__sound=sound).distinct()
    sound_has_bookmark_without_category = Bookmark.objects.filter(user=request.user, sound=sound, category=None).exists()
    add_bookmark_url = '/'.join(
        request.build_absolute_uri(reverse('add-bookmark', args=[sound_id])).split('/')[:-2]) + '/'
    tvars = {
        'bookmarks': Bookmark.objects.filter(user=request.user, sound=sound).exists(),
        'sound_id': sound.id,
        'form': form,
        'sound_has_bookmark_without_category': sound_has_bookmark_without_category,
        'categories_aready_containing_sound': categories_already_containing_sound,
        'add_bookmark_url': add_bookmark_url
    }
    template = 'bookmarks/modal_bookmark_sound.html' if using_beastwhoosh(request) else 'bookmarks/bookmark_form.html'
    return render(request, template, tvars)
