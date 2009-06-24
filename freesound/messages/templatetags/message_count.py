from django import template
from messages.models import Message

register = template.Library()

@register.simple_tag
def unread_message_count(user):
    return Message.objects.filter(user_to=user, is_archived=False, is_sent=False, is_read=False).count()