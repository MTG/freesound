from django import template
from sounds.models import Sound
from comments.models import Comment
from forum.models import Post

register = template.Library()

@register.inclusion_tag("accounts/active_user_content.html", takes_context=True)
def active_user_content(context,user_obj, content_type):
    content = None
    if content_type == "sound":
        content = Sound.objects.select_related().filter(user=user_obj).order_by("-created")[0]
    elif  content_type == "post":
        content = Post.objects.select_related().filter(author=user_obj).order_by("-created")[0]
    elif content_type == "comment":
        content = Comment.objects.select_related().filter(user=user_obj).order_by("-created")[0]
    return {'content_type':content_type,'content':content,'user':user_obj,'media_url': context['media_url']}
