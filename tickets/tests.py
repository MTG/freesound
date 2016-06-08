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

import hashlib

from django.contrib.auth.models import User
from django.test import TestCase
from models import Ticket, Queue
from tickets import QUEUE_SOUND_MODERATION, QUEUE_SUPPORT_REQUESTS
from tickets import TICKET_SOURCE_NEW_SOUND, TICKET_STATUS_NEW
from sounds.models import Sound
import sounds
import tickets


class TicketsTest(TestCase):
    fixtures = ['initial_data.json', 'moderation_test_users.json']

    def test_new_ticket(self):
        ticket = Ticket()
        ticket.source = 'contact_form'
        ticket.status = 'new'
        ticket.sender = User.objects.get(username='test_user')
        ticket.queue = Queue.objects.get(name=QUEUE_SUPPORT_REQUESTS)
        ticket.save()
        self.assertEqual(ticket.assignee, None)

    def test_new_ticket_linked_sound(self):
        test_user = User.objects.get(username='test_user')
        ticket = Ticket()
        ticket.source = 'new_sound'
        ticket.status = 'new'
        ticket.sender = User.objects.get(username='test_user')
        ticket.assignee = User.objects.get(username='test_moderator')
        ticket.queue = Queue.objects.get(name=QUEUE_SOUND_MODERATION)
        ticket.save()
        # just to test, this would be a sound object for example
        s = Sound(description='test sound', license_id=1, user=test_user)
        s.save()
        ticket.sound = s
        ticket.save()
        self.assertEqual(s.id, ticket.sound.id)

    def _create_test_sound(self, moderation_state, processing_state, user, filename):
        sound = sounds.models.Sound.objects.create(
                moderation_state=moderation_state,
                processing_state=processing_state,
                license=sounds.models.License.objects.get(pk=1),
                user=user,
                md5=hashlib.md5(filename).hexdigest(),
                original_filename=filename)
        return sound

    def _create_ticket(self, sound, user):
        ticket = tickets.models.Ticket.objects.create(
                title='Moderate sound test_sound.wav',
                source=TICKET_SOURCE_NEW_SOUND,
                status=TICKET_STATUS_NEW,
                queue=Queue.objects.get(name='sound moderation'),
                sender=user,
                sound=sound,
        )
        return ticket

    def test_new_sound_tickets_count(self):
        test_user = User.objects.get(username='test_user')
        sound = self._create_test_sound(moderation_state='PE', processing_state='OK',
                                        user=test_user, filename='test_sound1.wav')
        self._create_ticket(sound, test_user)

        # New ticket for a moderated sound doesn't count
        moderated_sound = self._create_test_sound(moderation_state='OK', processing_state='OK',
                                                  user=test_user, filename='test_sound2.wav')
        self._create_ticket(moderated_sound, test_user)

        # Accepted ticket doesn't count
        accepted_sound = self._create_test_sound(moderation_state='PE', processing_state='OK',
                                                 user=test_user, filename='test_sound3.wav')
        acc_ticket = self._create_ticket(accepted_sound, test_user)
        acc_ticket.status = tickets.TICKET_STATUS_ACCEPTED
        acc_ticket.save()

        # Ticket with an assigned moderator doesn't count
        assigned_sound = self._create_test_sound(moderation_state='PE', processing_state='OK',
                                                 user=test_user, filename='test_sound4.wav')
        assigned_ticket = self._create_ticket(assigned_sound, test_user)
        test_moderator = User.objects.get(username='test_moderator')
        assigned_ticket.assignee = test_moderator
        assigned_ticket.save()

        count = tickets.views.new_sound_tickets_count()
        self.assertEqual(1, count)
