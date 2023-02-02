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

from messages.models import Message

register = template.Library()


@register.inclusion_tag('messages/display_message.html', takes_context=True)
def display_message(context, message):
    return {
        'message': message,
        'hide_toggle_read_unread': context.get('hide_toggle_read_unread', False),
        'hide_archive_unarchive': context.get('hide_archive_unarchive', False),
        'list_type': context['list_type']
    }
