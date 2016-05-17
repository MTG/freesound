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

from django.core.management.base import BaseCommand
from tickets.models import Ticket
from tickets import TICKET_STATUS_CLOSED


class Command(BaseCommand):
    help = "Whitelist a user and close all pending tickets. Take as argument a ticket_id"
    args = True  # For backwards compatimility mdoe
    # See: http://stackoverflow.com/questions/30244288/django-management-command-cannot-see-arguments

    def handle(self,  *args, **options):

        ticket_id = str(args[0])
        ticket = Ticket.objects.get(id=ticket_id)
        whitelist_user = ticket.sender
        whitelist_user.profile.is_whitelisted = True
        whitelist_user.profile.save()
        pending_tickets = Ticket.objects.filter(sender=whitelist_user,
                                                source='new sound') \
                                        .exclude(status=TICKET_STATUS_CLOSED)
        # Set all sounds to OK and the tickets to closed
        for pending_ticket in pending_tickets:
            if pending_ticket.content:
                if pending_ticket.content.content_object is not None:
                    pending_ticket.content.content_object.change_moderation_state("OK")

            # This could be done with a single update, but there's a chance
            # we lose a sound that way (a newly created ticket who's sound
            # is not set to OK, but the ticket is closed).
            pending_ticket.status = TICKET_STATUS_CLOSED
            pending_ticket.save()
