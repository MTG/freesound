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

from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from models import Ticket, Queue, LinkedContent
from django.contrib.auth.models import User, Group
from tickets import QUEUE_BUG_REPORTS, QUEUE_MANAGEMENT, \
    QUEUE_SOUND_MODERATION, QUEUE_SUPPORT_REQUESTS

class CreateTickets(TestCase):
    
    fixtures = ['moderation_test_users.json']
    
    def setUp(self):
        # test client
        self.client      = Client()
    
    def test_new_ticket(self):
        ticket = Ticket()
        ticket.source = 'contact_form'
        ticket.status = 'new'
        ticket.sender = User.objects.get(username='test_user')
        ticket.queue = Queue.objects.get(name=QUEUE_SUPPORT_REQUESTS)
        ticket.save()
        self.assertEqual(ticket.assignee, None)
        
    def test_new_ticket_linked_content(self):
        ticket = Ticket()
        ticket.source = 'new_sound'
        ticket.status = 'new'
        ticket.sender = User.objects.get(username='test_user')
        ticket.assignee = User.objects.get(username='test_moderator')
        ticket.queue = Queue.objects.get(name=QUEUE_SOUND_MODERATION)
        ticket.save()
        lc = LinkedContent()
        # just to test, this would be a sound object for example
        lc.content_object = User.objects.get(username='test_admin')
        lc.save() 
        ticket.content = lc
        ticket.content.save()
        self.assertEqual(User.objects.get(username='test_admin').id, 
                         ticket.content.object_id)
