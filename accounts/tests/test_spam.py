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
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserFlag
from forum.models import Thread, Post, Forum
from messages.models import Message, MessageBody
from sounds.models import Sound


class ReportSpamOffensive(TestCase):
    """
    Test the "report spam/offensive" feature available for sound comments, forum posts and private messages.
    NOTE: for simplicity in  variable names, etc we only refer to the "spam" case.
    """

    fixtures = ['initial_data', 'sounds']

    def setUp(self):
        # Create users reporting spam
        self.reporters = []
        for i in range(0, settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING + 1):
            reporter = User.objects.create_user(username='reporter_{0}'.format(i),
                                                email='reporter_{0}@example.com'.format(i), password='testpass')
            self.reporters.append(reporter)

        # Create user posting spam
        self.spammer = User.objects.create_user(username='spammer', email='spammer@example.com', password='testpass')

    def get_reporter_as_logged_in_user(self, i):
        user = self.reporters[i]
        self.client.force_login(user=user)
        return user

    def __test_report_object(self, flag_type, object):

        # Flag the comment (no email to admins should be sent yet as only one reporter)
        reporter = self.get_reporter_as_logged_in_user(0)
        resp = self.client.post(reverse('flag-user', kwargs={'username': self.spammer.username}), data={
            'object_id': object.id,
            'flag_type': flag_type,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(UserFlag.objects.count(), 1)  # One flag object created
        self.assertEqual(UserFlag.objects.first().reporting_user, reporter)  # Flag object created by reporter
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Flag the same comment by other users so email is sent
        for i in range(1, settings.USERFLAG_THRESHOLD_FOR_NOTIFICATION):  # Start at 1 as first flag already done
            reporter = self.get_reporter_as_logged_in_user(i)
            resp = self.client.post(reverse('flag-user', kwargs={'username': self.spammer.username}), data={
                'object_id': object.id,
                'flag_type': flag_type,
            })
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(UserFlag.objects.count(), i + 1)  # Now we have more flags
            self.assertEqual(UserFlag.objects.all().order_by('id')[i].reporting_user,
                             reporter)  # Flag object created by reporter

            if i == settings.USERFLAG_THRESHOLD_FOR_NOTIFICATION - 1:  # Last iteration
                self.assertEqual(len(mail.outbox), 1)  # Notification email sent
                self.assertTrue("[freesound] Spam/offensive report for user" in mail.outbox[0].subject)
                self.assertTrue("has been reported" in mail.outbox[0].body)

        # Continue flagging object until it reaches blocked state
        for i in range(settings.USERFLAG_THRESHOLD_FOR_NOTIFICATION,
                       settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING):  # Start at 1 as first flag already done
            reporter = self.get_reporter_as_logged_in_user(i)
            resp = self.client.post(reverse('flag-user', kwargs={'username': self.spammer.username}), data={
                'object_id': object.id,
                'flag_type': flag_type,
            })
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(UserFlag.objects.count(), i + 1)  # Now we have more flags
            self.assertEqual(UserFlag.objects.all().order_by('id')[i].reporting_user,
                             reporter)  # Flag object created by reporter

            if i == settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING - 1:  # Last iteration
                self.assertEqual(len(mail.outbox), 2)  # New notification email sent
                self.assertTrue("[freesound] Spam/offensive report for user" in mail.outbox[1].subject)
                self.assertTrue("has been blocked" in mail.outbox[1].body)

            else:
                self.assertEqual(len(mail.outbox), 1)  # No new wmail sent

        # Flag the object again and no new notification emails are sent
        reporter = self.get_reporter_as_logged_in_user(settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING)
        resp = self.client.post(reverse('flag-user', kwargs={'username': self.spammer.username}), data={
            'object_id': object.id,
            'flag_type': flag_type,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(UserFlag.objects.count(), settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING + 1)
        self.assertEqual(len(mail.outbox), 2)  # New notification email sent

    def test_report_sound_comment(self):
        sound = Sound.objects.first()
        sound.add_comment(self.spammer, 'This is a spammy comment')
        comment = self.spammer.comment_set.first()
        self.__test_report_object('SC', comment)

    def test_report_forum_post(self):
        thread = Thread.objects.create(author=self.spammer, title="Span thread",
                                       forum=Forum.objects.create(name="Test forum"))
        object = Post.objects.create(author=self.spammer, thread=thread, body="Spam post post body")
        self.__test_report_object('FP', object)

    def test_report_private_message(self):
        object = Message.objects.create(user_from=self.spammer, user_to=self.reporters[0], subject='Spam subject',
                                        body=MessageBody.objects.create(body='Spam body'), is_sent=True,
                                        is_archived=False, is_read=False)
        self.__test_report_object('PM', object)

    def test_report_object_same_user(self):
        # Test that when a user is reported many times but not by distinct users, no email is sent
        # NOTE: we only test for the case of sound comments as the logic that handles this is common for all other
        # kinds of reports

        sound = Sound.objects.first()
        sound.add_comment(self.spammer, 'This is a spammy comment')
        comment = self.spammer.comment_set.first()

        # Flag the comment many times by the same user (no email to admins should be sent yet as only one reporter)
        reporter = self.get_reporter_as_logged_in_user(0)
        for i in range(0, settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING + 1):
            resp = self.client.post(reverse('flag-user', kwargs={'username': self.spammer.username}), data={
                'object_id': comment.id,
                'flag_type': 'SC',  # Sound comment
            })
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(UserFlag.objects.count(), i + 1)
            self.assertEqual(len(mail.outbox), 0)  # No email sent

    def test_report_multiple_objects(self):
        # Make spammy objects
        sound = Sound.objects.first()
        sound.add_comment(self.spammer, 'This is a spammy comment')
        comment = self.spammer.comment_set.first()
        thread = Thread.objects.create(author=self.spammer, title="Span thread",
                                       forum=Forum.objects.create(name="Test forum"))
        post = Post.objects.create(author=self.spammer, thread=thread, body="Spam post post body")
        message = Message.objects.create(user_from=self.spammer, user_to=self.reporters[0], subject='Spam subject',
                                         body=MessageBody.objects.create(body='Spam body'), is_sent=True,
                                         is_archived=False, is_read=False)
        objects_flag_types = [
            (comment, 'SC'),
            (post, 'FP'),
            (message, 'PM'),
        ]

        # Report objects by distinct users
        for i in range(0, settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING + 1):
            reporter = self.get_reporter_as_logged_in_user(i)
            object, flag_type = objects_flag_types[i % len(objects_flag_types)]
            resp = self.client.post(reverse('flag-user', kwargs={'username': self.spammer.username}), data={
                'object_id': object.id,
                'flag_type': flag_type,
            })
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(UserFlag.objects.count(), i + 1)
            self.assertEqual(UserFlag.objects.all().order_by('id')[i].reporting_user,
                             reporter)  # Flag object created by reporter

            if i == settings.USERFLAG_THRESHOLD_FOR_NOTIFICATION - 1:  # Last iteration
                self.assertEqual(len(mail.outbox), 1)  # New notification email sent
                self.assertTrue("[freesound] Spam/offensive report for user" in mail.outbox[0].subject)
                self.assertTrue("has been reported" in mail.outbox[0].body)
            elif i == settings.USERFLAG_THRESHOLD_FOR_AUTOMATIC_BLOCKING - 1:
                self.assertEqual(len(mail.outbox), 2)  # New notification email sent
                self.assertTrue("[freesound] Spam/offensive report for user" in mail.outbox[1].subject)
                self.assertTrue("has been blocked" in mail.outbox[1].body)
