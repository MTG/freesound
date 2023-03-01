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


from django import template
from django.contrib.auth.models import User

from accounts.models import Profile
from follow import follow_utils

register = template.Library()


@register.inclusion_tag('accounts/display_user.html', takes_context=True)
def display_user(context, user, size='small', comment_created=None, donated_amount=None):
    """This templatetag is used to display a user with some information next to it. It prepares some variables that
    are then passed to the display_user.html template to show user information.

    Args:
        context (django.template.Context): an object with contextual information for rendering a template. This
          argument is automatically added by Django when calling the templatetag inside a template.
        user (int or User): user ID or User object of the user that will be shown. If no user exists for the
          given ID, the display_user.html will be rendered with empty HTML.
        size (str, optional): size or "flavour" of the player to display. Different pages might need to render users
          differently, so this parameter allows to choose that. Information about the contents of each
          size is given in the display_user.html template code.
        donated_amount (str, optional): donation amount label (including currency name) displayed for "top_donor" size

    Returns:
        dict: dictionary with the variables needed for rendering the user with the display_user.html template

    """

    if isinstance(user, User):
        user_obj = user
    else:
        try:
            user_obj = User.objects.get(id=user)
        except User.DoesNotExist:
            user_obj = None

    if user_obj is None:
        return {
            'user': None,
        }
    else:
        request = context['request']

        is_followed_by_request_user = None
        if size == 'follow_lists':
            is_followed_by_request_user = request.user.is_authenticated \
                                          and follow_utils.is_user_following_user(request.user, user_obj)

        return {
            'user': user_obj,
            'user_profile_locations': Profile.locations_static(user_obj.id, user_obj.profile.has_avatar),
            'media_url': context['media_url'],
            'request': request,
            'is_followed_by_request_user': is_followed_by_request_user,
            'comment_created': comment_created,
            'donated_amount': donated_amount,
            'next_path': context['next_path'],
            'size': size,
        }


@register.inclusion_tag('accounts/display_user.html', takes_context=True)
def display_user_follow_lists(context, user):
    return display_user(context, user, size='follow_lists')


@register.inclusion_tag('accounts/display_user.html', takes_context=True)
def display_user_top_donor(context, user, donated_amount):
    return display_user(context, user, size='top_donor', donated_amount=donated_amount)


@register.inclusion_tag('accounts/display_user.html', takes_context=True)
def display_user_comment(context, user, comment_created):
    return display_user(context, user, size='comment', comment_created=comment_created)
