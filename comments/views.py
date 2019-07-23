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

from comments.models import Comment
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response, render
from django.template.context import RequestContext
from django.db import transaction
from sounds.models import Sound
from utils.pagination import paginate
from utils.username import redirect_if_old_username_or_404


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
    page = request.GET.get("page")
    return HttpResponseRedirect(next+"?page="+page)


@redirect_if_old_username_or_404
def for_user(request, username):
    """ Display all comments for the sounds of the user """
    user = request.parameter_user
    sounds = Sound.objects.filter(user=user)
    qs = Comment.objects.filter(sound__in=sounds).select_related("user", "user__profile")
    paginator = paginate(request, qs, 30)
    comments = paginator["page"].object_list
    tvars = {
        "user": user,
        "comments": comments,
        "mode": "for_user"
    }
    tvars.update(paginator)
    return render(request, 'sounds/comments.html', tvars)


@redirect_if_old_username_or_404
def by_user(request, username):
    """ Display all comments made by the user """
    user = request.parameter_user
    qs = Comment.objects.filter(user=user).select_related("user", "user__profile")
    paginator = paginate(request, qs, 30)
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
    qs = Comment.objects.select_related("user", "user__profile")
    paginator = paginate(request, qs, 30)
    comments = paginator["page"].object_list
    tvars = {
        "comments": comments,
        "mode": "latest"
    }
    tvars.update(paginator)
    return render(request, 'sounds/comments.html', tvars)

