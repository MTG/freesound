from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from comments.models import Comment
from sounds.models import Sound
from django.contrib import messages
from django.core.exceptions import PermissionDenied

@login_required
def delete(request, comment_id):
    print "in comment delete"

    try:
        comment = Comment.objects.get(id=comment_id)
        print comment
    except Comment.DoesNotExist:
        raise PermissionDenied
    
    if comment.content_type == ContentType.objects.get_for_model(Sound):
        sound = Sound.objects.get(id=comment.object_id)

        if not (request.user.has_perm('sound.can_change') or sound.user == request.user):
            raise PermissionDenied

        comment.delete()
        messages.success(request, 'Comment deleted.')

        sound.num_comments = sound.num_comments - 1
        sound.save()
        
        return HttpResponseRedirect(sound.get_absolute_url())
    else:
        raise PermissionDenied