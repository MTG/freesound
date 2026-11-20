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

import datetime

import pytest
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.urls import reverse
from zenpy.lib.api import serialize

from comments.models import Comment
from support.views import _should_add_api_datapacks_tag, create_zendesk_ticket, send_email_to_support


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
    user = User.objects.get(email=request_email)
    user.last_login = datetime.datetime(2024, 2, 3, tzinfo=datetime.timezone.utc)
    user.save()
    user.profile.num_sounds = 3
    user.profile.num_posts = 7
    user.profile.save()
    Comment.objects.create(user=user, comment="First comment")
    Comment.objects.create(user=user, comment="Second comment")
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)

    # Check that ticket loaded users' email and username correctly
    assert sticket["requester"]["email"] == request_email
    assert sticket["requester"]["name"] == "test_user"

    # Check that ticket added custom fields
    assert len(sticket["custom_fields"]) == 6
    assert {field["id"]: field["value"] for field in sticket["custom_fields"]} == {
        30294425: True,
        30294725: user.date_joined.date().isoformat(),
        30153569: "2024-02-03",
        30295025: 3,
        30295045: 7,
        30153729: 2,
    }

    # Check that ticket extended description with user info as expected
    user_url = f"https://{Site.objects.get_current().domain}{reverse('account', args=[user.username])}"
    assert sticket["description"] == f"{message}\n\n-- \n{user_url}"
    assert sticket["subject"] == subject

    # Try with non-existing email address
    request_email = "test.user+1234678235@gmail.com"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)
    assert sticket["requester"]["email"] == request_email
    assert sticket["requester"]["name"] == "Unknown username"  # Set unknown username
    assert "custom_fields" not in sticket  # no custom fields
    assert sticket["description"] == message  # No extra description
    assert sticket["subject"] == subject


def test_api_datapacks_tag_matching():
    """Test the keyword matching logic for API and datapacks tags"""
    # Should match "api" as a full word (case-insensitive)
    assert _should_add_api_datapacks_tag("Problem with API")
    assert _should_add_api_datapacks_tag("api request")
    assert _should_add_api_datapacks_tag("API AUTHENTICATION")
    assert _should_add_api_datapacks_tag("Help with the API please")

    # Should not match "api" when it's part of another word
    assert not _should_add_api_datapacks_tag("Graphic problem")
    assert not _should_add_api_datapacks_tag("Captcha issues")

    # Should match "data pack" as full words
    assert _should_add_api_datapacks_tag("Issue with data pack")
    assert _should_add_api_datapacks_tag("Data pack download")
    assert _should_add_api_datapacks_tag("DATA PACK help")

    # Should match "datapack" as a full word
    assert _should_add_api_datapacks_tag("Question about datapack")
    assert _should_add_api_datapacks_tag("DATAPACK issues")

    # Should match "commercial"
    assert _should_add_api_datapacks_tag("Commercial use inquiry")
    assert _should_add_api_datapacks_tag("commercial API")
    assert _should_add_api_datapacks_tag("COMMERCIAL license")

    # Should not match partial words
    assert not _should_add_api_datapacks_tag("datapacking issues")

    # Should not match unrelated subjects
    assert not _should_add_api_datapacks_tag("Account issue")
    assert not _should_add_api_datapacks_tag("Audio quality question")


def test_create_zendesk_ticket_with_api_tag(moderation_test_users):
    """Test that API-related subjects get the api-datapacks tag"""
    request_email = "test.user+1@gmail.com"

    # Test with API in subject
    subject = "Problem with API authentication"
    message = "I'm having trouble with the API"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)
    assert "tags" in sticket
    assert "api-datapacks" in sticket["tags"]

    # Test with data pack in subject
    subject = "Download data pack"
    message = "How do I download the data pack?"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)
    assert "tags" in sticket
    assert "api-datapacks" in sticket["tags"]

    # Test with datapack in subject
    subject = "Datapack license"
    message = "Question about datapack"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)
    assert "tags" in sticket
    assert "api-datapacks" in sticket["tags"]

    # Test with commercial in subject
    subject = "Commercial API usage"
    message = "We want to use the API commercially"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)
    assert "tags" in sticket
    assert "api-datapacks" in sticket["tags"]

    # Test without API/datapack keywords
    subject = "Account issue"
    message = "I cannot log in"
    ticket = create_zendesk_ticket(request_email, subject, message)
    sticket = serialize(ticket)
    assert "tags" not in sticket or "api-datapacks" not in sticket.get("tags", [])


def test_create_zendesk_ticket_api_assignee(moderation_test_users, settings):
    """Test that API-related tickets are assigned to ZENDESK_API_REQUESTS_ASIGNEE_ID"""
    request_email = "test.user+1@gmail.com"
    settings.ZENDESK_API_REQUESTS_ASIGNEE_ID = 123456

    ticket = create_zendesk_ticket(request_email, "Problem with API authentication", "Help")
    assert serialize(ticket)["assignee_id"] == 123456

    ticket = create_zendesk_ticket(request_email, "Account issue", "I cannot log in")
    assert "assignee_id" not in serialize(ticket)

    # If the setting is empty, no assignee is set
    settings.ZENDESK_API_REQUESTS_ASIGNEE_ID = ""
    ticket = create_zendesk_ticket(request_email, "Problem with API authentication", "Help")
    assert "assignee_id" not in serialize(ticket)
