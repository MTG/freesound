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

import pytest
from zenpy.lib.api import serialize

from support.views import create_zendesk_ticket, send_email_to_support


@pytest.fixture
def moderation_test_users(load_fixtures):
    load_fixtures(["moderation_test_users"])


def test_send_support_request_email(moderation_test_users, settings, mailoutbox):
    settings.SUPPORT = (("Name", "email@freesound.org"),)
    subject = "test subject"
    message = "test message"

    # try with existing email address
    request_email = "test.user+1@gmail.com"
    send_email_to_support(request_email, subject, message)
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["email@freesound.org"]
    assert mailoutbox[0].extra_headers["Reply-To"] == request_email
    assert subject in mailoutbox[0].subject
    assert message in mailoutbox[0].body

    # try with non-existing email address
    request_email = "test.user+1234678235@gmail.com"
    send_email_to_support(request_email, subject, message)
    assert len(mailoutbox) == 2
    assert mailoutbox[1].to == ["email@freesound.org"]
    assert mailoutbox[1].extra_headers["Reply-To"] == request_email
    assert subject in mailoutbox[1].subject
    assert message in mailoutbox[1].body


def test_create_zendesk_ticket(moderation_test_users):
    subject = "test subject"
    message = "test message"

    # Try with existing email address
    request_email = "test.user+1@gmail.com"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)

    # Check that ticket loaded users' email and username correctly
    assert sticket["requester"]["email"] == request_email
    assert sticket["requester"]["name"] == "test_user"

    # Check that ticket added custom fields
    assert "custom_fields" in sticket

    # Check that ticket extended description with user info as expected
    assert len(sticket["description"]) > len(message)

    # Try with non-existing email address
    request_email = "test.user+1234678235@gmail.com"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)
    assert sticket["requester"]["email"] == request_email
    assert sticket["requester"]["name"] == "Unknown username"  # Set unknown username
    assert "custom_fields" not in sticket  # no custom fields
    assert len(sticket["description"]) == len(message)  # No extra description
