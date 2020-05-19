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
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import EmailPreferenceType, UserEmailSetting


class MessageReceivedEmailNotification(TestCase):
    """
    Test that email notifications are sent correctly when a message is received
    """

    fixtures = ['email_preference_type']

    def setUp(self):
        self.sender = User.objects.create_user(username='sender', email='sender@example.com')
        self.receiver = User.objects.create_user(username='receiver', email='receiver@example.com')

    @override_settings(RECAPTCHA_PUBLIC_KEY='')
    def test_message_email_preference_enabled(self):
        self.client.force_login(user=self.sender)
        resp = self.client.post(reverse('messages-new'), data={
            u'body': [u'test message body'],
            u'to': [u'receiver'],
            u'subject': [u'test message'],
        })
        self.assertRedirects(resp, reverse('messages'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(settings.EMAIL_SUBJECT_PREFIX in mail.outbox[0].subject)
        self.assertTrue(settings.EMAIL_SUBJECT_PRIVATE_MESSAGE in mail.outbox[0].subject)

    @override_settings(RECAPTCHA_PUBLIC_KEY='')
    def test_message_email_preference_disabled(self):
        # Create email preference object for the email type (which will mean user does not want message emails as
        # it is enabled by default and the preference indicates user does not want it).
        email_pref = EmailPreferenceType.objects.get(name="private_message")
        UserEmailSetting.objects.create(user=self.receiver, email_type=email_pref)

        self.client.force_login(user=self.sender)
        resp = self.client.post(reverse('messages-new'), data={
            u'body': [u'test message body'],
            u'to': [u'receiver'],
            u'subject': [u'test message'],
        })
        self.assertRedirects(resp, reverse('messages'))
        self.assertEqual(len(mail.outbox), 0)
