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

import os

import mock
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

import accounts.models
from accounts.management.commands.process_email_bounces import process_message, decode_idna_email
from accounts.models import EmailPreferenceType, EmailBounce
from accounts.views import handle_uploaded_image
from sounds.models import Pack
from tags.models import TaggedItem
from utils.mail import send_mail
from utils.test_helpers import override_avatars_path_with_temp_directory


class ProfileGetUserTags(TestCase):
    fixtures = ['sounds_with_tags']

    def test_user_tagcloud_solr(self):
        user = User.objects.get(username="Anton")
        mock_solr = mock.Mock()
        conf = {
            'select.return_value': {
                'facet_counts': {
                    'facet_ranges': {},
                    'facet_fields': {'tag': ['conversation', 1, 'dutch', 1, 'glas', 1, 'glass', 1, 'instrument', 2,
                                             'laughter', 1, 'sine-like', 1, 'struck', 1, 'tone', 1, 'water', 1]},
                    'facet_dates': {},
                    'facet_queries': {}
                },
                'responseHeader': {
                    'status': 0,
                    'QTime': 4,
                    'params': {'fq': 'username:\"Anton\"', 'facet.field': 'tag', 'f.tag.facet.limit': '10',
                               'facet': 'true', 'wt': 'json', 'f.tag.facet.mincount': '1', 'fl': 'id', 'qt': 'dismax'}
                },
                'response': {'start': 0, 'numFound': 48, 'docs': []}
            }
        }
        mock_solr.return_value.configure_mock(**conf)
        accounts.models.Solr = mock_solr
        tag_names = [item["name"] for item in list(user.profile.get_user_tags(use_solr=True))]
        used_tag_names = list(set([item.tag.name for item in TaggedItem.objects.filter(user=user)]))
        non_used_tag_names = list(set([item.tag.name for item in TaggedItem.objects.exclude(user=user)]))

        # Test that tags retrieved with get_user_tags are those found in db
        self.assertEqual(len(set(tag_names).intersection(used_tag_names)), len(tag_names))
        self.assertEqual(len(set(tag_names).intersection(non_used_tag_names)), 0)

        # Test solr not available return False
        conf = {'select.side_effect': Exception}
        mock_solr.return_value.configure_mock(**conf)
        self.assertEqual(user.profile.get_user_tags(use_solr=True), False)

    def test_user_tagcloud_db(self):
        user = User.objects.get(username="Anton")
        tag_names = [item["name"] for item in list(user.profile.get_user_tags(use_solr=False))]
        used_tag_names = list(set([item.tag.name for item in TaggedItem.objects.filter(user=user)]))
        non_used_tag_names = list(set([item.tag.name for item in TaggedItem.objects.exclude(user=user)]))

        # Test that tags retrieved with get_user_tags are those found in db
        self.assertEqual(len(set(tag_names).intersection(used_tag_names)), len(tag_names))
        self.assertEqual(len(set(tag_names).intersection(non_used_tag_names)), 0)


class UserEditProfile(TestCase):
    fixtures = ['email_preference_type']

    @override_avatars_path_with_temp_directory
    def test_handle_uploaded_image(self):
        user = User.objects.create_user("testuser", password="testpass")
        f = InMemoryUploadedFile(open(settings.MEDIA_ROOT + '/images/70x70_avatar.png'), None, None, None, None, None)
        handle_uploaded_image(user.profile, f)

        # Test that avatar files were created
        self.assertEqual(os.path.exists(user.profile.locations("avatar.S.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.M.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.L.path")), True)

    def test_edit_user_profile(self):
        User.objects.create_user("testuser", password="testpass")
        self.client.login(username='testuser', password='testpass')
        self.client.post("/home/edit/", {
            'profile-home_page': 'http://www.example.com/',
            'profile-username': 'testuser',
            'profile-about': 'About test text',
            'profile-signature': 'Signature test text',
            'profile-not_shown_in_online_users_list': True,
        })

        user = User.objects.select_related('profile').get(username="testuser")
        self.assertEqual(user.profile.home_page, 'http://www.example.com/')
        self.assertEqual(user.profile.about, 'About test text')
        self.assertEqual(user.profile.signature, 'Signature test text')
        self.assertEqual(user.profile.not_shown_in_online_users_list, True)

        # Now we change the username the maximum allowed times
        for i in range(settings.USERNAME_CHANGE_MAX_TIMES):
            self.client.post("/home/edit/", {
                'profile-home_page': 'http://www.example.com/',
                'profile-username': 'testuser%d' % i,
                'profile-about': 'About test text',
                'profile-signature': 'Signature test text',
                'profile-not_shown_in_online_users_list': True,
            })

            user = User.objects.get(username="testuser%d" % i)
            self.assertEqual(user.old_usernames.count(), i + 1)

        # Now the form should fail when we try to change the username
        resp = self.client.post("/home/edit/", {
            'profile-home_page': 'http://www.example.com/',
            'profile-username': 'testuser-error',
            'profile-about': 'About test text',
            'profile-signature': 'Signature test text',
            'profile-not_shown_in_online_users_list': True,
        })

        self.assertNotEqual(resp.context['profile_form'].errors, None)

    def test_edit_user_email_settings(self):
        EmailPreferenceType.objects.create(name="email", display_name="email")
        User.objects.create_user("testuser", password="testpass")
        self.client.login(username='testuser', password='testpass')
        response = self.client.post("/home/email-settings/", {
            'email_types': 1,
        })
        user = User.objects.select_related('profile').get(username="testuser")
        email_types = user.profile.get_enabled_email_types()
        self.assertEqual(len(email_types), 1)
        self.assertTrue(email_types.pop().name, 'email')

    @override_avatars_path_with_temp_directory
    def test_edit_user_avatar(self):
        User.objects.create_user("testuser", password="testpass")
        self.client.login(username='testuser', password='testpass')
        self.client.post("/home/edit/", {
            'image-file': open(settings.MEDIA_ROOT + '/images/70x70_avatar.png'),
            'image-remove': False,
        })

        user = User.objects.select_related('profile').get(username="testuser")
        self.assertEqual(user.profile.has_avatar, True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.S.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.M.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.L.path")), True)

        self.client.post("/home/edit/", {
            'image-file': '',
            'image-remove': True,
        })
        user = User.objects.select_related('profile').get(username="testuser")
        self.assertEqual(user.profile.has_avatar, False)


class AboutFieldVisibilityTest(TestCase):
    """Verifies visibility of about field"""

    def setUp(self):
        self.spammer = User.objects.create_user(username='spammer', email='spammer@example.com', password='testpass')
        self.downloader = User.objects.create_user(username='downloader', email='downloader@example.com',
                                                   password='testpass')
        self.uploader = User.objects.create_user(username='uploader', email='uploader@example.com', password='testpass')
        self.admin = User.objects.create_user(username='admin', email='admin@example.com', password='testpass',
                                              is_superuser=True)

        self.downloader.profile.num_sound_downloads = 1
        self.uploader.profile.num_sounds = 1

        self.about = 'Non-empty about field'
        for user in [self.spammer, self.downloader, self.uploader, self.admin]:
            user.profile.about = self.about
            user.profile.save()

    def _check_visibility(self, username, condition):
        resp = self.client.get(reverse('account', kwargs={'username': username}))
        if condition:
            self.assertIn(self.about, resp.content)
        else:
            self.assertNotIn(self.about, resp.content)

    def _check_visible(self):
        self._check_visibility('downloader', True)
        self._check_visibility('uploader', True)
        self._check_visibility('admin', True)

    def test_anonymous(self):
        self._check_visibility('spammer', False)
        self._check_visible()

    def test_spammer(self):
        self.client.login(username='spammer', password='testpass')
        self._check_visibility('spammer', True)
        self._check_visible()

    def test_admin(self):
        self.client.login(username='admin', password='testpass')
        self._check_visibility('spammer', True)
        self._check_visible()


class EmailBounceTest(TestCase):
    """Test things related to email bounce info from AWS"""

    @staticmethod
    def _send_mail(user_to):
        return send_mail('Test subject', 'Test body', user_to=user_to)

    @mock.patch('utils.mail.get_connection')
    def test_send_mail(self, get_connection):
        user = User.objects.create_user('user', email='user@freesound.org')
        self.assertTrue(self._send_mail(user))

        email_bounce = EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)
        self.assertFalse(user.profile.email_is_valid())
        self.assertFalse(self._send_mail(user))

        email_bounce.delete()
        self.assertTrue(user.profile.email_is_valid())
        self.assertTrue(self._send_mail(user))

    def test_unactivated_user_deleted(self):
        user = User.objects.create_user('user', email='user@freesound.org')
        user.is_active = False
        user.save()
        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)
        call_command('cleanup_unactivated_users')

        with self.assertRaises(User.DoesNotExist):
            user.refresh_from_db()

    def test_activated_user_not_deleted(self):
        user = User.objects.create_user('user', email='user@freesound.org')
        user.is_active = True
        user.save()
        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)
        call_command('cleanup_unactivated_users')
        try:
            user.refresh_from_db()
        except User.DoesNotExist:
            self.fail()

    def test_unactivated_user_with_content_not_deleted(self):
        # Should never happen, testing the has_content safety check if something goes wrong
        user = User.objects.create_user('user', email='user@freesound.org')
        user.is_active = False
        user.save()
        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)

        # Somehow user created pack without being activated
        pack = Pack.objects.create(user=user, name="Ghost pack")

        # Regular run should not delete the user, because we check for content
        call_command('cleanup_unactivated_users')
        try:
            user.refresh_from_db()
        except User.DoesNotExist:
            self.fail()

        # Fast run (without safety check) should delete the user and pack
        call_command('cleanup_unactivated_users', fast=True)
        with self.assertRaises(User.DoesNotExist):
            user.refresh_from_db()
        with self.assertRaises(Pack.DoesNotExist):
            pack.refresh_from_db()

    def test_request_email_change(self):
        user = User.objects.create_user('user', email='user@freesound.org', password='testpass')
        self.client.login(username='user', password='testpass')
        resp = self.client.get(reverse('front-page'))
        self.assertEquals(resp.status_code, 200)

        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)
        resp = self.client.get(reverse('front-page'))
        self.assertRedirects(resp, reverse('accounts-email-reset'))

    def test_populate_bounce(self):
        message_body = {
            "bounceType": "Permanent",
            "bounceSubType": "Suppressed",
            "bouncedRecipients": [{"emailAddress": "user@freesound.org"}],
            "timestamp": "2018-05-20T13:54:37.821Z"
        }

        user = User.objects.create_user('user', email='user@freesound.org')
        process_message(message_body)
        self.assertFalse(user.profile.email_is_valid())

    def test_idna_email(self):
        encoded_email = u'user@xn--eb-tbv.de'
        decoded_email = u'user@\u2211eb.de'
        self.assertEquals(decoded_email, decode_idna_email(encoded_email))


class ProfileEmailIsValid(TestCase):

    def test_email_is_valid(self):
        user = User.objects.create_user('user', email='user@freesound.org', is_active=False)

        # Test newly created user (still not activated) has email valid
        # NOTE: we send activation emails to inactive users, therefore email is valid
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.profile.email_is_valid(), True)

        # Test newly created user (after activation) also has email valid
        user.is_active = True
        user.save()
        self.assertEqual(user.profile.email_is_valid(), True)

        # Test email becomes invalid when it bounced in the past
        email_bounce = EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)
        self.assertEqual(user.profile.email_is_valid(), False)
        email_bounce.delete()
        self.assertEqual(user.profile.email_is_valid(), True)  # Back to normal

        # Test email becomes invalid when user is deleted (anonymized)
        user.profile.delete_user()
        self.assertEqual(user.profile.email_is_valid(), False)

        # Test email is still invalid after user is deleted and bounces happened
        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)
        self.assertEqual(user.profile.email_is_valid(), False)
