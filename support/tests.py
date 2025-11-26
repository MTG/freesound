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

from django.test import TestCase
from django.test.utils import override_settings
from support.views import send_email_to_support, create_zendesk_ticket
from zenpy.lib.api import serialize


class SupportRequestsTest(TestCase):
    fixtures = ["moderation_test_users"]

    @override_settings(SUPPORT=(("Name", "email@freesound.org"),))
    def test_send_support_request_email(self):
        subject = "test subject"
        message = "test message"

        # try with existing email address
        request_email = "test.user+1@gmail.com"
        send_email_to_support(request_email, subject, message)
        self.assertTrue(True)  # This call is not really needed, but makes sense to me

        # try with non-existing email address
        request_email = "test.user+1234678235@gmail.com"
        send_email_to_support(request_email, subject, message)
        self.assertTrue(True)  # This call is not really needed, but makes sense to me

    def test_create_zendesk_ticket(self):
        subject = "test subject"
        message = "test message"

        # Try with existing email address
        request_email = "test.user+1@gmail.com"
        ticket = create_zendesk_ticket(request_email, subject, message)
        sticket = serialize(ticket)

        # Check that ticket loaded users' email and username correctly
        self.assertEqual(sticket["requester"]["email"], request_email)
        self.assertEqual(sticket["requester"]["name"], "test_user")

        # Check that ticket added custom fields
        self.assertTrue("custom_fields" in sticket)

        # Check that ticket extended description with user info as expected
        self.assertTrue(len(sticket["description"]) > len(message))

        # Try with non-existing email address
        request_email = "test.user+1234678235@gmail.com"
        ticket = create_zendesk_ticket(request_email, subject, message)
        sticket = serialize(ticket)
        self.assertEqual(sticket["requester"]["email"], request_email)
        self.assertEqual(sticket["requester"]["name"], "Unknown username")  # Set unknown username
        self.assertTrue("custom_fields" not in sticket)  # no custom fields
        self.assertTrue(len(sticket["description"]) == len(message))  # No extra description
