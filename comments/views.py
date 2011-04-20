from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from comments.models import Comment
from sounds.models import Sound
from django.contrib import messages
from django.core.exceptions import PermissionDenied

@login_required
def delete(request, comment_id):

    comment = get_object_or_404(Comment, id=comment_id)

    if not (request.user.has_perm('comments.delete_comment') \
            or (comment.content_object.user == request.user \
                if comment.content_object and hasattr(comment.content_object, 'user') \
                else False)):
        raise PermissionDenied

    comment.delete()
    messages.success(request, 'Comment deleted.')

    if comment.content_type == ContentType.objects.get_for_model(Sound):
        sound = comment.content_object
        sound.num_comments = sound.num_comments - 1
        sound.save()

    return HttpResponseRedirect(sound.get_absolute_url())
