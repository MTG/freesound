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
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from messages.models import Message, MessageBody
from messages.views import get_previously_contacted_usernames, quote_message_for_reply


class RecaptchaPresenceInMessageForms(TestCase):
    """
    Test whether the recapctha field should or should not be present in new message/reply message forms.
    """

    fixtures = ['licenses']

    def setUp(self):
        # Create one user which is a potential spammer and one which is not
        self.no_spammer = User.objects.create_user(username='noSpammer', email='noSpammer@example.com')
        self.no_spammer.profile.num_sounds = 4  # Having sounds will make user "trustable"
        self.no_spammer.profile.save()

        self.potential_spammer = User.objects.create_user(
            username='potentialSpammer', email='potentialSpammer@example.com')

        self.message_sender = User.objects.create_user(username='sender', email='sender@example.com')

    def test_captcha_presence_in_new_message_form(self):

        # Not a spammer case, recaptcha field should NOT be shown
        self.client.force_login(user=self.no_spammer)
        resp = self.client.get(reverse('messages-new'))
        self.assertNotContains(resp, 'recaptcha')

        # Potential spammer (has no uploaded sounds), recaptcha field should be shown
        self.client.force_login(user=self.potential_spammer)
        resp = self.client.get(reverse('messages-new'))
        self.assertContains(resp, 'recaptcha')

    def test_captcha_presence_in_reply_message_form(self):

        # Test non spammer does not see recaptcha field in reply form
        message = Message.objects.create(
            user_from=self.message_sender, user_to=self.no_spammer, subject='Message subject',
            body=MessageBody.objects.create(body='Message body'), is_sent=True, is_archived=False, is_read=False)
        self.client.force_login(user=self.no_spammer)
        resp = self.client.get(reverse('messages-new', args=[message.id]))
        self.assertNotContains(resp, 'recaptcha')

        # Potential spammer (has no uploaded sounds), recaptcha field should be shown
        message = Message.objects.create(
            user_from=self.message_sender, user_to=self.potential_spammer, subject='Message subject',
            body=MessageBody.objects.create(body='Message body'), is_sent=True, is_archived=False, is_read=False)
        self.client.force_login(user=self.potential_spammer)
        resp = self.client.get(reverse('messages-new', args=[message.id]))
        self.assertContains(resp, 'recaptcha')


class UsernameLookup(TestCase):
    """
    Test the username lookup functionality used when writing new messages
    """

    def setUp(self):
        # Create user and message objects that should appear in the username lookup
        self.sender = User.objects.create_user(username='sender', email='sender@example.com')
        self.receiver1 = User.objects.create_user(username='receiver1', email='receiver1@example.com')
        self.receiver2 = User.objects.create_user(username='receiver2', email='receiver2@example.com')
        self.receiver3 = User.objects.create_user(username='receiver3', email='receiver3@example.com')
        self.sender2 = User.objects.create_user(username='sender2', email='sender2@example.com')

        # Send 1 message to receiver1, 2 messages to receiver2 and 3 messages to receiver3
        for count, receiver in enumerate([self.receiver1, self.receiver2, self.receiver3]):
            for _ in range(0, count + 1):
                Message.objects.create(
                    user_from=self.sender, user_to=receiver, subject='Message subject',
                    body=MessageBody.objects.create(body='Message body'),
                    is_sent=True, is_archived=False, is_read=False)

        # Send one message from sender2 to sender1
        Message.objects.create(
            user_from=self.sender2, user_to=self.sender, subject='Message subject',
            body=MessageBody.objects.create(body='Message body'),
            is_sent=True, is_archived=False, is_read=False)

    def test_username_lookup_num_queries(self):
        # Check that username lookup view only makes 1 query
        with self.assertNumQueries(1):
            get_previously_contacted_usernames(self.sender)

    def test_get_previously_contacted_usernames(self):
        # Check get_previously_contacted_usernames helper function returns userames of users previously contacted by
        # the sender or users who previously contacted the sender
        self.assertCountEqual([self.receiver3.username, self.receiver2.username, self.receiver1.username,
                                    self.sender2.username, self.sender.username],
                             get_previously_contacted_usernames(self.sender))

    def test_username_lookup_response(self):
        # Check username lookup view returns userames of users previously contacted by the sender or users who
        # previously contacted the sender
        self.client.force_login(self.sender)
        resp = self.client.get(reverse('messages-username_lookup'))
        response_json = json.loads(resp.content)
        self.assertEqual(resp.status_code, 200)
        self.assertCountEqual([self.receiver3.username, self.receiver2.username, self.receiver1.username,
                                    self.sender2.username, self.sender.username],
                             response_json)


class QuoteMessageTestCase(TestCase):
    def test_oneline(self):
        body = "This is a message"
        username = "testuser"

        new_body = quote_message_for_reply(body, username)
        expected = "> --- testuser wrote:\n>\n> This is a message"
        self.assertEqual(new_body, expected)

    def test_manylines(self):
        body = "This is a message\nwith multiple lines"
        username = "testuser"

        new_body = quote_message_for_reply(body, username)
        expected = "> --- testuser wrote:\n>\n> This is a message\n> with multiple lines"
        self.assertEqual(new_body, expected)


    def test_alreadyquoted(self):
        body = "This is a message\n> with already quoted lines"
        username = "testuser"

        new_body = quote_message_for_reply(body, username)
        expected = "> --- testuser wrote:\n>\n> This is a message\n>> with already quoted lines"
        self.assertEqual(new_body, expected)

    def test_removetags(self):
        body = '<span>This is a <b>message</b></span>\n<!--comment-->\n<a href="link">more</a>'
        username = "testuser"

        new_body = quote_message_for_reply(body, username)
        expected = "> --- testuser wrote:\n>\n> This is a message\n> comment\n> more"
        self.assertEqual(new_body, expected)

    def test_wrap(self):
        body = "A message that is more than 60 characters long. I need lots of text for the test"
        username = "testuser"

        new_body = quote_message_for_reply(body, username)
        expected = "> --- testuser wrote:\n>\n> A message that is more than 60 characters long. I need lots\n> of text for the test"
        self.assertEqual(new_body, expected)
