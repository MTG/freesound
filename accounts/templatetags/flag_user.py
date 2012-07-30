from django import template
from comments.models import Comment
from forum.models import Post
from messages.models import Message
from accounts.models import UserFlag
register = template.Library()

@register.inclusion_tag("accounts/flag_user.html", takes_context=True)
def flag_user(context, flag_type, username, content_id, text = None, user_sounds = None):

    no_show = False
    link_text = "Report spam"

    print context['request'].user
    print context['request'].user.is_authenticated()

    if not context['request'].user.is_authenticated():
        no_show = True
        flagged = []
    else:
        flagged = UserFlag.objects.filter(user__username = username, reporting_user = context['request'].user, object_id = content_id).values('reporting_user').distinct()
        if text:
            link_text = text

    return {'user_sounds':user_sounds,'done_text':"Marked as spam", 'flagged':len(flagged),'flag_type':flag_type,'username':username, 'content_obj_id':content_id, 'media_url': context['media_url'], 'link_text':link_text, 'no_show':no_show}
