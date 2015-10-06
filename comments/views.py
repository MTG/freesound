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
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext
from sounds.models import Sound
from utils.functional import combine_dicts
from utils.pagination import paginate


@login_required
def delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if not (request.user.has_perm('comments.delete_comment') or
            (comment.content_object.user == request.user if comment.content_object and
                hasattr(comment.content_object, 'user') else False)
            ):
        raise PermissionDenied
    comment.delete()
    messages.success(request, 'Comment deleted.')

    if comment.content_type == ContentType.objects.get_for_model(Sound):
        sound = comment.content_object
        sound.post_delete_comment()
        
    next = request.GET.get("next")
    page = request.GET.get("page")
    return HttpResponseRedirect(next+"?page="+page)


def for_user(request, username):
    """ This is all very hacky because GenericRelations don't allow you to span
    relations with select_related... hence we get the content_objects and then
    load all the sounds related to those in a big lookup. If we don't do this
    the page generates about 90+ queries, with it we only generate 4 queries :-) """
    user = get_object_or_404(User, username__iexact=username)
    sound_type = ContentType.objects.get_for_model(Sound)
    qs = Comment.objects.filter(content_type=sound_type, sound__user=user).select_related("user", "user__profile")
    paginator_obj = paginate(request, qs, 30)
    comments = paginator_obj["page"].object_list
    sound_ids = set([comment.object_id for comment in comments])
    sound_lookup = dict([(sound.id, sound) for sound in list(Sound.objects.filter(id__in=sound_ids))])
    for comment in comments:
        comment.sound_object = sound_lookup[comment.object_id]
    return render_to_response('sounds/comments_for_user.html', combine_dicts(paginator_obj, locals()), context_instance=RequestContext(request))

def all(request):
    """ This is all very hacky because GenericRelations don't allow you to span
    relations with select_related... hence we get the content_objects and then
    load all the sounds related to those in a big lookup. If we don't do this
    the page generates about 90+ queries, with it we only generate 4 queries :-) """
    sound_type = ContentType.objects.get_for_model(Sound)
    qs = Comment.objects.filter(content_type=sound_type).select_related("user", "user__profile")
    paginator_obj = paginate(request, qs, 30)
    comments = paginator_obj["page"].object_list
    sound_ids = set([comment.object_id for comment in comments])
    sound_lookup = dict([(sound.id, sound) for sound in list(Sound.objects.filter(id__in=sound_ids).select_related("user"))])
    for comment in comments:
        comment.sound_object = sound_lookup[comment.object_id]
    return render_to_response('sounds/comments.html', combine_dicts(paginator_obj, locals()), context_instance=RequestContext(request))