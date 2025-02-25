# Authors:
#     See AUTHORS file.
#


from django import template
from django.conf import settings

from accounts.models import User

register = template.Library()


@register.inclusion_tag('molecules/object_selector.html', takes_context=True)
def users_selector(context, users, selected_user_ids=[], show_select_all_buttons=False):
    if users:
        if not isinstance(users[0], User):
            # users are passed as a list of user ids, retrieve the Sound objects from DB
            users = User.objects.ordered_ids(users)
        for user in users:
            user.selected = user.id in selected_user_ids
    return {
        'objects': users,
        'type': 'users',
        'show_select_all_buttons': show_select_all_buttons,
        'original_context': context  # This will be used so a nested inclusion tag can get the original context
    }