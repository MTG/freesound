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
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from comments.models import Comment
from sounds.models import Sound
from utils.frontend_handling import render, using_beastwhoosh
from utils.pagination import paginate
from utils.username import redirect_if_old_username_or_404, raise_404_if_user_is_deleted


@login_required
@transaction.atomic()
def delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    # User can delete if has permission or if is the owner of the comment
    if not (request.user.has_perm('comments.delete_comment'))\
            and comment.user != request.user:
        # Also user can delete if is the owner of the sound
        if not comment.sound or comment.sound.user != request.user:
            raise PermissionDenied
    comment.delete()
    comment.sound.invalidate_template_caches()
    messages.success(request, 'Comment deleted.')
    next = request.GET.get("next")
    page = request.GET.get("page", None)
    if page is not None:
        next = next+"?page="+page
    return HttpResponseRedirect(next + "#comments")


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def for_user(request, username):
    """ Display all comments for the sounds of the user """
    if using_beastwhoosh(request) and not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse('account', args=[username]) + '?comments=1')
        
    user = request.parameter_user
    sounds = Sound.objects.filter(user=user)
    qs = Comment.objects.filter(sound__in=sounds).select_related("user", "user__profile",
                                                                 "sound__user", "sound__user__profile")
    num_items_per_page = 30 if not using_beastwhoosh(request) else settings.COMMENTS_IN_MODAL_PER_PAGE_BW
    paginator = paginate(request, qs, num_items_per_page)
    if using_beastwhoosh(request):
        page = paginator["page"]
        sound_ids = [d.sound_id for d in page]
        sounds_dict = Sound.objects.dict_ids(sound_ids)
        for comment in page.object_list:
            comment.sound_object = sounds_dict[comment.sound_id]
        tvars = {
            "user": user,
            "mode": "for_user",
            "delete_next_url": reverse('account', args=[username]) + f'?comments={paginator["current_page"]}'
        }
        tvars.update(paginator)
        return render(request, 'accounts/modal_comments.html', tvars)
    else:
        comments = paginator["page"].object_list
        tvars = {
            "user": user,
            "comments": comments,
            "mode": "for_user"
        }
        tvars.update(paginator)
        return render(request, 'sounds/comments.html', tvars)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def by_user(request, username):
    """ Display all comments made by the user """
    if using_beastwhoosh(request) and not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse('account', args=[username]) + '?comments_by=1')
    
    user = request.parameter_user
    qs = Comment.objects.filter(user=user).select_related("user", "user__profile",
                                                          "sound__user", "sound__user__profile")
    num_items_per_page = 30 if not using_beastwhoosh(request) else settings.COMMENTS_IN_MODAL_PER_PAGE_BW
    paginator = paginate(request, qs, num_items_per_page)
    if using_beastwhoosh(request):
        page = paginator["page"]
        sound_ids = [d.sound_id for d in page]
        sounds_dict = Sound.objects.dict_ids(sound_ids)
        for comment in page.object_list:
            comment.sound_object = sounds_dict[comment.sound_id]
        tvars = {
            "user": user,
            "mode": "by_user",
            "delete_next_url": reverse('account', args=[username]) + f'?comments_by={paginator["current_page"]}'
        }
        tvars.update(paginator)
        return render(request, 'accounts/modal_comments.html', tvars)
    else:
        comments = paginator["page"].object_list
        tvars = {
            "user": user,
            "comments": comments,
            "mode": "by_user"
        }
        tvars.update(paginator)
        return render(request, 'sounds/comments.html', tvars)

def all(request):
    """ Display all comments """
    qs = Comment.objects.select_related("user", "user__profile", "sound__user", "sound__user__profile")
    paginator = paginate(request, qs, 30)
    comments = paginator["page"].object_list
    tvars = {
        "comments": comments,
        "mode": "latest"
    }
    tvars.update(paginator)
    return render(request, 'sounds/comments.html', tvars)

