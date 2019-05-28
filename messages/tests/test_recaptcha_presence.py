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

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from messages.models import Message, MessageBody


class RecaptchaPresenceInMessageForms(TestCase):
    """
    Test that whether the recapctha field should or should not be present in new message/reply message forms.
    """

    fixtures = ['initial_data']

    def setUp(self):
        # Create one user which is a potential spammer and one which is not
        self.no_spammer = User.objects.create_user(username='noSpammer', email='noSpammer@example.com')
        self.no_spammer.profile.num_sounds = 4  # Having sounds will make user "trustable"
        self.no_spammer.profile.save()

        self.potential_spammer = User.objects.create_user(
            username='potentialSpammer', email='potentialSpammer@example.com')

        self.message_sender = User.objects.create_user(username='sender', email='sender@example.com')

    def test_captcha_presence_in_new_message_form(self):

        # No spammer case, recaptcha field should NOT be shown
        self.client.force_login(user=self.no_spammer)
        resp = self.client.get(reverse('messages-new'))
        self.assertNotIn('recaptcha', resp.content)

        # Potential spammer (has no uploaded sounds), recaptcha field should be shown
        self.client.force_login(user=self.potential_spammer)
        resp = self.client.get(reverse('messages-new'))
        self.assertIn('recaptcha', resp.content)

    def test_captcha_presence_in_reply_message_form(self):

        # Test non spammer does not see recaptcha field in reply form
        message = Message.objects.create(
            user_from=self.message_sender, user_to=self.no_spammer, subject='Message subject',
            body=MessageBody.objects.create(body='Message body'), is_sent=True, is_archived=False, is_read=False)
        self.client.force_login(user=self.no_spammer)
        resp = self.client.get(reverse('messages-new', args=[message.id]))
        self.assertNotIn('recaptcha', resp.content)

        # Potential spammer (has no uploaded sounds), recaptcha field should be shown
        message = Message.objects.create(
            user_from=self.message_sender, user_to=self.potential_spammer, subject='Message subject',
            body=MessageBody.objects.create(body='Message body'), is_sent=True, is_archived=False, is_read=False)
        self.client.force_login(user=self.potential_spammer)
        resp = self.client.get(reverse('messages-new', args=[message.id]))
        self.assertIn('recaptcha', resp.content)
