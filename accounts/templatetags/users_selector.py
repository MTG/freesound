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
from django.conf import settings

from accounts.models import User

register = template.Library()


@register.inclusion_tag('molecules/object_selector.html', takes_context=True)
def users_selector(context, users, selected_user_ids=None, show_select_all_buttons=False):
    if users:
        if not isinstance(users[0], User):
            # users are passed as a list of user ids, retrieve the User objects from DB
            users = User.objects.ordered_ids(users)
        if selected_user_ids != None:
            for user in users:
                user.selected = user.id in selected_user_ids
    return {
        'objects': users,
        'type': 'users',
        'show_select_all_buttons': show_select_all_buttons,
        'original_context': context 
    }