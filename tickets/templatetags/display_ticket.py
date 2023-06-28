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

from sounds.models import Sound

register = template.Library()


@register.inclusion_tag('moderation/display_ticket.html', takes_context=True)
def display_ticket(context, ticket, sound=None, include_last_message=False):
    if sound == None:
        if ticket.sound_id is not None:
            sound = Sound.objects.bulk_query_id(sound_ids=ticket.sound_id)[0]
        else:
            sound = None
    ticket_messages = ticket.messages.all()
    num_messages = len(ticket_messages)
    tvars = {
        'request': context['request'],
        'media_url': context['media_url'],
        'ticket': ticket,
        'sound': sound,
        'include_last_message': include_last_message,
        'num_messages': num_messages,
        'last_message': ticket_messages[0] if num_messages and include_last_message else None
    }
    return tvars

@register.inclusion_tag('moderation/display_ticket.html', takes_context=True)
def display_ticket_with_message(context, ticket, sound=None):
    return display_ticket(context, ticket, sound=sound, include_last_message=True)
