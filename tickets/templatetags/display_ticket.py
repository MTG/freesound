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
def display_ticket(context, ticket, include_last_message=False):
    if not hasattr(ticket, 'sound_obj'):
        if ticket.sound_id is not None:
            sound = Sound.objects.bulk_query_id(sound_ids=ticket.sound_id)[0]
        else:
            sound = None
    else:
        sound = ticket.sound_obj
    if not hasattr(ticket, 'num_messages'):
        ticket_messages = ticket.messages.all()
        num_messages = len(ticket_messages)
    else:
        ticket_messages = None
        num_messages = ticket.num_messages

    if not hasattr(ticket, 'last_message'):
        if ticket_messages is None:
            ticket_messages = ticket.messages.all()
        last_message = ticket_messages[0] if num_messages and include_last_message else None
        if last_message is not None:
            last_message_text = last_message.text
            last_message_sender_username = last_message.sender.username
        else:
            last_message_text = None
            last_message_sender_username = None
    else:
        last_message = ticket.last_message
        if last_message is not None:
            last_message_text = last_message['text']
            last_message_sender_username = last_message['sender_username']

    tvars = {
        'request': context['request'],
        'ticket': ticket,
        'sound': sound,
        'num_messages': num_messages,
        'include_last_message': include_last_message,
        'last_message_text': last_message_text,
        'last_message_sender_username': last_message_sender_username,
    }
    return tvars


@register.inclusion_tag('moderation/display_ticket.html', takes_context=True)
def display_ticket_with_message(context, ticket):
    return display_ticket(context, ticket, include_last_message=True)
