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

from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
import hashlib

import mock
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

import sounds
import tickets
from .models import Ticket, Queue
from sounds.models import Sound
from tickets import QUEUE_SOUND_MODERATION
from tickets import TICKET_STATUS_NEW, TICKET_STATUS_ACCEPTED, TICKET_STATUS_CLOSED, TICKET_STATUS_DEFERRED
from tickets.forms import IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY, IS_EXPLICIT_ADD_FLAG_KEY, IS_EXPLICIT_REMOVE_FLAG_KEY


class NewTicketTests(TestCase):
    fixtures = ['licenses', 'user_groups', 'moderation_queues', 'moderation_test_users']

    def test_new_ticket(self):
        """New tickets shouldn't have an assignee"""
        ticket = Ticket()
        ticket.status = 'new'
        ticket.sender = User.objects.get(username='test_user')
        ticket.queue = Queue.objects.get(name=QUEUE_SOUND_MODERATION)
        ticket.save()
        self.assertEqual(ticket.assignee, None)

    def test_new_ticket_linked_sound(self):
        """Sound should be properly linked to the ticket"""
        test_user = User.objects.get(username='test_user')
        ticket = Ticket()
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


class TicketTests(TestCase):
    """Superclass that has several helper methods"""
    fixtures = ['licenses', 'user_groups', 'moderation_queues', 'moderation_test_users']

    @staticmethod
    def _create_test_sound(user, filename='test_sound.wav', moderation_state='PE', processing_state='OK'):
        """Creates a sound with specified states"""
        sound = sounds.models.Sound.objects.create(
            moderation_state=moderation_state,
            processing_state=processing_state,
            license=sounds.models.License.objects.get(pk=1),
            user=user,
            md5=hashlib.md5(filename.encode()).hexdigest(),
            original_filename=filename)
        return sound

    @staticmethod
    def _create_ticket(sound, user, ticket_status=TICKET_STATUS_NEW, ticket_assignee=None):
        """Creates a ticket with specified parameters"""
        ticket = tickets.models.Ticket.objects.create(
            title='Moderate sound test_sound.wav',
            queue=Queue.objects.get(name='sound moderation'),
            status=ticket_status,
            sender=user,
            sound=sound,
            assignee=ticket_assignee
        )
        return ticket

    def setUp(self):
        """Gets references to user and moderator, creates a sound and logs in as moderator"""
        self.test_user = User.objects.get(username='test_user')
        self.test_moderator = User.objects.get(username='test_moderator')
        self.sound = self._create_test_sound(self.test_user)
        self.client.force_login(self.test_moderator)

    def _create_assigned_ticket(self):
        """Creates ticket that is already assigned to the moderator"""
        return self._create_ticket(self.sound, self.test_user, ticket_status=TICKET_STATUS_ACCEPTED,
                                   ticket_assignee=self.test_moderator)


class MiscTicketTests(TicketTests):

    def test_new_sound_tickets_count(self):
        """New ticket count should only include new tickets without an assignee"""
        # Normal ticket that is new and unassigned
        self.ticket = self._create_ticket(self.sound, self.test_user)

        # New ticket for a moderated sound doesn't count
        moderated_sound = self._create_test_sound(self.test_user, filename='test_sound2.wav', moderation_state='OK')
        self._create_ticket(moderated_sound, self.test_user)

        # Accepted ticket doesn't count
        accepted_sound = self._create_test_sound(self.test_user, filename='test_sound3.wav')
        self._create_ticket(accepted_sound, self.test_user, ticket_status=TICKET_STATUS_ACCEPTED)

        # Ticket with an assigned moderator doesn't count
        assigned_sound = self._create_test_sound(self.test_user, filename='test_sound4.wav')
        self._create_ticket(assigned_sound, self.test_user, ticket_assignee=self.test_moderator)

        count = tickets.views.new_sound_tickets_count()
        self.assertEqual(1, count)

    @mock.patch('tickets.models.send_mail_template')
    def test_send_notification_user(self, send_mail_mock):
        """Emails should be properly configured and sent with notifications"""
        ticket = self._create_assigned_ticket()

        ticket.send_notification_emails(
                tickets.models.Ticket.NOTIFICATION_APPROVED_BUT,
                tickets.models.Ticket.USER_ONLY)

        local_vars = {
                'ticket': ticket,
                'user_to': ticket.sender,
                }
        send_mail_mock.assert_called_once_with(
                settings.EMAIL_SUBJECT_MODERATION_HANDLED,
                tickets.models.Ticket.NOTIFICATION_APPROVED_BUT,
                local_vars,
                user_to=ticket.sender)


class TicketTestsFromQueue(TicketTests):
    """Ticket state changes in a response to actions from moderation queue"""

    def setUp(self):
        TicketTests.setUp(self)
        self.ticket = self._create_assigned_ticket()

    def _perform_action(self, action):
        return self.client.post(reverse('tickets-moderation-assigned', args=[self.test_moderator.id]), {
            'action': action, 'message': u'', 'ticket': self.ticket.id,
            'is_explicit': IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY})

    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_delete_ticket_from_queue(self, delete_sound_solr):
        resp = self._perform_action(u'Delete')

        self.assertEqual(resp.status_code, 200)
        delete_sound_solr.assert_called_once_with([self.sound.id])

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, TICKET_STATUS_CLOSED)
        self.assertIsNone(self.ticket.sound)

    @mock.patch('general.tasks.whitelist_user.delay')
    def test_whitelist_from_queue(self, whitelist_task):
        self._perform_action(u'Whitelist')
        whitelist_task.assert_called_once_with(ticket_ids=[self.ticket.id])

    def _assert_ticket_and_sound_fields(self, status, assignee, moderation_state):
        self.ticket.refresh_from_db()
        self.ticket.sound.refresh_from_db()
        self.assertEqual(self.ticket.status, status)
        self.assertEqual(self.ticket.sound.moderation_state, moderation_state)
        if assignee is None:
            self.assertIsNone(self.ticket.assignee)
        else:
            self.assertEqual(self.ticket.assignee, assignee)

    def test_approve_ticket_from_queue(self):
        resp = self._perform_action(u'Approve')
        self.assertEqual(resp.status_code, 200)
        self._assert_ticket_and_sound_fields(TICKET_STATUS_CLOSED, self.test_moderator, 'OK')

    def test_return_ticket_from_queue(self):
        resp = self._perform_action(u'Return')
        self.assertEqual(resp.status_code, 200)
        self._assert_ticket_and_sound_fields(TICKET_STATUS_NEW, None, 'PE')

    def test_defer_ticket_from_queue(self):
        resp = self._perform_action(u'Defer')
        self.assertEqual(resp.status_code, 200)
        self._assert_ticket_and_sound_fields(TICKET_STATUS_DEFERRED, self.test_moderator, 'PE')


class TicketTestsFromTicketViewOwn(TicketTestsFromQueue):
    """Ticket state changes in a response to actions from ticket inspection page for own ticket"""
    def _perform_action(self, action):
        return self.client.post(reverse('tickets-ticket', args=[self.ticket.key]), {
            'ss-action': action})


class TicketTestsFromTicketViewNew(TicketTestsFromQueue):
    """Ticket state changes in a response to actions from ticket inspection page for new ticket"""
    def setUp(self):
        TicketTests.setUp(self)
        self.ticket = self._create_ticket(self.sound, self.test_user)

    def _perform_action(self, action):
        return self.client.post(reverse('tickets-ticket', args=[self.ticket.key]), {
            'ss-action': action})


class TicketTestsIsExplicitFlagFromQueue(TicketTests):
    """Test that the is_explicit flag of moderated sounds changes in accordance to moderator's choices"""

    def setUp(self):
        TicketTests.setUp(self)
        self.ticket = self._create_assigned_ticket()

    def _perform_action(self, action, is_explicit_flag_key):
        return self.client.post(reverse('tickets-moderation-assigned', args=[self.test_moderator.id]), {
            'action': action, 'message': u'', 'ticket': self.ticket.id, 'is_explicit': is_explicit_flag_key})

    def test_keep_is_explicit_preference_for_explicit_sound(self):
        """Test that when approving a sound marked as 'is_explicit' it continues to be marked as such the moderator
        chooses to preserve author's preference on the flag
        """
        self.ticket.sound.is_explicit = True
        self.ticket.sound.save()
        self._perform_action(u'Approve', IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY)
        self.ticket.sound.refresh_from_db()
        self.assertEqual(self.ticket.sound.is_explicit, True)

    def test_keep_is_explicit_preference_for_non_explicit_sound(self):
        """Test that when approving a sound not marked as 'is_explicit', the flag does not get added if the moderator
        chooses to preserve author's preference on the flag
        """
        self.ticket.sound.is_explicit = False
        self.ticket.sound.save()
        self._perform_action(u'Approve', IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY)
        self.ticket.sound.refresh_from_db()
        self.assertEqual(self.ticket.sound.is_explicit, False)

    def test_add_is_explicit_flag_for_explicit_sound(self):
        """Test that when apporving a sound it's 'is_explicit' flag is set to True if the moderator chooses to add
        the explicit flag
        """
        self.ticket.sound.is_explicit = True
        self.ticket.sound.save()
        self._perform_action(u'Approve', IS_EXPLICIT_ADD_FLAG_KEY)
        self.ticket.sound.refresh_from_db()
        self.assertTrue(self.ticket.sound.is_explicit)

    def test_add_is_explicit_flag_for_non_explicit_sound(self):
        """Test that when apporving a sound it's 'is_explicit' flag is set to True if the moderator chooses to add
        the explicit flag, even if the sound was originally marked as non explicit
        """
        self.ticket.sound.is_explicit = False
        self.ticket.sound.save()
        self._perform_action(u'Approve', IS_EXPLICIT_ADD_FLAG_KEY)
        self.ticket.sound.refresh_from_db()
        self.assertTrue(self.ticket.sound.is_explicit)

    def test_remove_is_explicit_flag_for_non_explicit_sound(self):
        """Test that when apporving a sound it's 'is_explicit' flag is set to False if the moderator chooses to remove
        the explicit flag
        """
        self.ticket.sound.is_explicit = False
        self.ticket.sound.save()
        self._perform_action(u'Approve', IS_EXPLICIT_REMOVE_FLAG_KEY)
        self.ticket.sound.refresh_from_db()
        self.assertFalse(self.ticket.sound.is_explicit)

    def test_remove_is_explicit_flag_for_explicit_sound(self):
        """Test that when apporving a sound it's 'is_explicit' flag is set to False if the moderator chooses to remove
        the explicit flag, even if the sound was originally marked as explicit
        """
        self.ticket.sound.is_explicit = True
        self.ticket.sound.save()
        self._perform_action(u'Approve', IS_EXPLICIT_REMOVE_FLAG_KEY)
        self.ticket.sound.refresh_from_db()
        self.assertFalse(self.ticket.sound.is_explicit)
