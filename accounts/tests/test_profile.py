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
import os
from unittest import mock

import freezegun
from dateutil.parser import parse as parse_date
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils.http import int_to_base36
import pytest

import accounts.models
from accounts.management.commands.process_email_bounces import process_message, decode_idna_email
from accounts.models import EmailPreferenceType, EmailBounce, UserEmailSetting
from accounts.views import handle_uploaded_image
from forum.models import Forum, Thread, Post
from sounds.models import Pack, Download, PackDownload
from tags.models import SoundTag
from utils.mail import send_mail
from utils.test_helpers import override_avatars_path_with_temp_directory, create_user_and_sounds


@pytest.mark.django_db
class ProfileTest:

    def test_get_stats_for_profile_page(self, use_dummy_cache_backend, client):
        call_command('loaddata', 'licenses', 'sounds_with_tags')
        user = User.objects.get(username="Anton")

        response = client.get(reverse('account-stats-section', kwargs={'username': user.username}) + '?ajax=1')
        assert response.status_code == 200
        assert "2:51 minutes" in response.content.decode('utf-8')

        sound = user.sounds.all()[0]
        sound.duration = 3600 + 1260
        sound.save()

        response = client.get(reverse('account-stats-section', kwargs={'username': user.username}) + '?ajax=1')
        assert response.status_code == 200
        assert "1:23 hours" in response.content.decode('utf-8')


class ProfileGetUserTags(TestCase):
    fixtures = ['licenses', 'sounds_with_tags']

    def test_user_tagcloud_solr(self):
        user = User.objects.get(username="Anton")
        mock_search_engine = mock.Mock()
        conf = {
            'get_user_tags.return_value': [
                ('conversation', 1),
                ('dutch', 1),
                ('glas', 1),
                ('glass', 1),
                ('instrument', 2),
                ('laughter', 1),
                ('sine-like', 1),
                ('struck', 1),
                ('tone', 1),
                ('water', 1)
            ]
        }
        mock_search_engine.return_value.configure_mock(**conf)
        accounts.models.get_search_engine = mock_search_engine
        tag_names = [item['name'] for item in user.profile.get_user_tags()]
        used_tag_names = list({item.tag.name for item in SoundTag.objects.filter(user=user)})
        non_used_tag_names = list({item.tag.name for item in SoundTag.objects.exclude(user=user)})

        # Test that tags retrieved with get_user_tags are those found in db
        self.assertEqual(len(set(tag_names).intersection(used_tag_names)), len(tag_names))
        self.assertEqual(len(set(tag_names).intersection(non_used_tag_names)), 0)

        # Test search engine not available return False
        conf = {'get_user_tags.side_effect': Exception}
        mock_search_engine.return_value.configure_mock(**conf)
        self.assertEqual(user.profile.get_user_tags(), False)


class UserEditProfile(TestCase):
    fixtures = ['email_preference_type']

    @override_avatars_path_with_temp_directory
    def test_handle_uploaded_image(self):
        user = User.objects.create_user("testuser")
        STATIC_PUBLIC_BASE_DIR = 'freesound/static/bw-frontend/public/'
        test_avatar_path = os.path.join(STATIC_PUBLIC_BASE_DIR, 'test_avatar.png')
        with open(test_avatar_path, 'rb') as f:
            f = InMemoryUploadedFile(f, None, None, None, None, None)
            handle_uploaded_image(user.profile, f)

        # Test that avatar files were created
        self.assertEqual(os.path.exists(user.profile.locations("avatar.S.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.M.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.L.path")), True)

    def test_edit_user_profile(self):
        user = User.objects.create_user("testuser")
        self.client.force_login(user)
        resp = self.client.post("/home/edit/", {
            'profile-home_page': 'http://www.example.com/',
            'profile-username': 'testuser',
            'profile-about': 'About test text',
            'profile-signature': 'Signature test text',
            'profile-ui_theme_preference': 'd',            
        })

        user = User.objects.select_related('profile').get(username="testuser")
        self.assertEqual(user.profile.home_page, 'http://www.example.com/')
        self.assertEqual(user.profile.about, 'About test text')
        self.assertEqual(user.profile.signature, 'Signature test text')
        self.assertEqual(user.profile.ui_theme_preference, 'd')

        # Now we change the username the maximum allowed times
        for i in range(settings.USERNAME_CHANGE_MAX_TIMES):
            self.client.post("/home/edit/", {
                'profile-home_page': 'http://www.example.com/',
                'profile-username': 'testuser%d' % i,
                'profile-about': 'About test text',
                'profile-signature': 'Signature test text',
                'profile-ui_theme_preference': 'd',
            })

            user.refresh_from_db()
            self.assertEqual(user.old_usernames.count(), i + 1)

        # Now the "username" field in the form will be "disabled" because maximum number of username changes has been
        # reached. Therefore, the contents of "profile-username" in the POST request should have no effect and username
        # should not be changed any further
        self.client.post("/home/edit/", {
            'profile-home_page': 'http://www.example.com/',
            'profile-username': 'testuser-error',
            'profile-about': 'About test text',
            'profile-signature': 'Signature test text',
            'profile-ui_theme_preference': 'd',
        })
        user.refresh_from_db()
        self.assertEqual(user.old_usernames.count(), settings.USERNAME_CHANGE_MAX_TIMES)

    def test_edit_user_email_settings(self):
        EmailPreferenceType.objects.create(name="email", display_name="email")
        user = User.objects.create_user("testuser")
        self.client.force_login(user)
        response = self.client.post("/home/email-settings/", {
            'email_types': 1,
        })
        user = User.objects.select_related('profile').get(username="testuser")
        email_types = user.profile.get_enabled_email_types()
        self.assertEqual(len(email_types), 1)
        self.assertTrue(email_types.pop().name, 'email')

    @override_avatars_path_with_temp_directory
    def test_edit_user_avatar(self):
        user = User.objects.create_user("testuser")
        self.client.force_login(user)
        STATIC_PUBLIC_BASE_DIR = 'freesound/static/bw-frontend/public/'
        test_avatar_path = os.path.join(STATIC_PUBLIC_BASE_DIR, 'test_avatar.png')
        with open(test_avatar_path, 'rb') as f:
            self.client.post("/home/edit/", {
                'image-file': f,
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
        self.spammer = User.objects.create_user(username='spammer', email='spammer@example.com')
        self.downloader = User.objects.create_user(username='downloader', email='downloader@example.com')
        self.uploader = User.objects.create_user(username='uploader', email='uploader@example.com')
        self.admin = User.objects.create_user(username='admin', email='admin@example.com', is_superuser=True)

        self.downloader.profile.num_sound_downloads = 1
        self.uploader.profile.num_sounds = 1

        self.about = 'Non-empty about field'
        for user in [self.spammer, self.downloader, self.uploader, self.admin]:
            user.profile.about = self.about
            user.profile.save()

    def _check_visibility(self, username, condition):
        resp = self.client.get(reverse('account', kwargs={'username': username}))
        if condition:
            self.assertContains(resp, self.about)
        else:
            self.assertNotContains(resp, self.about)

    def _check_visible(self):
        self._check_visibility('downloader', True)
        self._check_visibility('uploader', True)
        self._check_visibility('admin', True)

    def test_anonymous(self):
        self._check_visibility('spammer', False)
        self._check_visible()

    def test_spammer(self):
        self.client.force_login(self.spammer)
        self._check_visibility('spammer', True)
        self._check_visible()

    def test_admin(self):
        self.client.force_login(self.admin)
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
        user = User.objects.create_user('user', email='user@freesound.org')
        self.client.force_login(user)
        cache.clear()  # Need to clear cache here to avoid 'random_sound' cache key being set
        resp = self.client.get(reverse('front-page'))
        self.assertEqual(resp.status_code, 200)
        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)
        cache.clear()  # Need to clear cache here to avoid 'random_sound' cache key being set
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
        encoded_email = 'user@xn--eb-tbv.de'
        decoded_email = 'user@\u2211eb.de'
        self.assertEqual(decoded_email, decode_idna_email(encoded_email))

    def test_email_email_bounce_removed_when_resetting_email(self):
        """when a user resets her email, related EmailBounce objects should be removed"""
        user = User.objects.create_user('user', email='user@freesound.org', password='12345')
        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)

        # User fills in email reset form
        self.client.force_login(user)
        resp = self.client.post(reverse('accounts-email-reset'), {
            'email': 'new_email@freesound.org',
            'password': '12345',
        })
        self.assertRedirects(resp, reverse('accounts-email-reset-done'))

        # User goes to link to complete email reset (which is sent by email)
        uid = int_to_base36(user.id)
        token = default_token_generator.make_token(user)
        self.client.get(reverse('accounts-email-reset-complete', args=[uid, token]))

        # Now asses no EmailBounce still exist
        self.assertEqual(EmailBounce.objects.filter(user=user).count(), 0)

    def test_email_email_bounce_removed_when_resetting_email_via_admin(self):
        """when an admin resets user's email, related EmailBounce objects should be removed as well"""
        user = User.objects.create_user('user', email='user@freesound.org')
        EmailBounce.objects.create(user=user, type=EmailBounce.PERMANENT)

        # Admin changes user's email address via admin page
        admin_user = User.objects.create_user('admin_user', email='admin_user@freesound.org',
                                              is_staff=True, is_superuser=True)
        self.client.force_login(admin_user)
        resp = self.client.post(reverse('admin:auth_user_change', args=[user.id]), data={
            'username': user.username,
            'email': 'new_email@freesound.org',
            'date_joined_0': "2015-10-06",
            'date_joined_1': "16:42:00"
        })
        user.refresh_from_db()
        self.assertEqual(user.email, 'new_email@freesound.org')

        # Now asses no EmailBounce still exist
        self.assertEqual(EmailBounce.objects.filter(user=user).count(), 0)


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


class ProfilePostInForumTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("testuser", email='email@freesound.org')
        self.forum = Forum.objects.create(name="testForum", name_slug="test_forum", description="test")
        self.thread = Thread.objects.create(forum=self.forum, title="testThread", author=self.user)

    def test_can_post_in_forum_unmoderated(self):
        """If you have an unmoderated post, you can't make another post"""
        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="NM")
        can_post, reason = self.user.profile.can_post_in_forum()
        self.assertFalse(can_post)
        self.assertIn("you have previous posts", reason)

    def test_can_post_in_forum_time(self):
        """If you have no sounds, you can't post within 5 minutes of the last one"""
        created = parse_date("2019-02-03 10:50:00 UTC")
        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()
        self.user.profile.refresh_from_db()
        with freezegun.freeze_time("2019-02-03 10:52:30", tz_offset=0):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertFalse(can_post)
            self.assertIn("was less than 5", reason)

        with freezegun.freeze_time("2019-02-03 11:03:30", tz_offset=0):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertTrue(can_post)

    def test_can_post_in_forum_has_sounds(self):
        """If you have sounds you can post even within 5 minutes of the last one"""
        created = parse_date("2019-02-03 10:50:00 UTC")
        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()
        self.user.profile.num_sounds = 3
        self.user.profile.save()
        self.user.profile.refresh_from_db()
        with freezegun.freeze_time("2019-02-03 10:52:30", tz_offset=0):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertTrue(can_post)

    def test_can_post_in_forum_numposts(self):
        """If you have no sounds, you can't post more than x posts per day.
        this is 5 + d^2 posts, where d is the number of days between your first post and now"""
        # our first post, 2 days ago
        created = parse_date("2019-02-03 10:50:00 UTC")

        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()

        # 2 days later, the maximum number of posts we can make today will be 5 + 4 = 9
        today = parse_date("2019-02-05 01:50:00 UTC")
        for i in range(9):
            post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
            today = today + datetime.timedelta(minutes=i+10)
            post.created = today
            post.save()
        self.user.profile.refresh_from_db()

        # After making 9 posts, we can't make any more
        with freezegun.freeze_time("2019-02-05 14:52:30", tz_offset=0):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertFalse(can_post)
            self.assertIn("you exceeded your maximum", reason)

    def test_can_post_in_forum_admin(self):
        """If you're a forum admin, you can post even if you have no sounds, you're within
        5 minutes of the last one, and you've gone over the limit of posts for the day"""
        created = parse_date("2019-02-03 10:50:00 UTC")
        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()
        perm = Permission.objects.get_by_natural_key('can_moderate_forum', 'forum', 'post')
        self.user.user_permissions.add(perm)

        with freezegun.freeze_time("2019-02-04 10:00:30", tz_offset=0):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertTrue(can_post)


class ProfileIsTrustWorthy(TestCase):
    """
    Test the is_truthworthy method of Profile model
    """

    def setUp(self):
        self.user = User.objects.create_user(username='user', email='user@example.com')

    def test_user_trustworthy_when_has_uploaded_sounds(self):
        self.assertFalse(self.user.profile.is_trustworthy())
        self.user.profile.num_sounds = 1
        self.user.profile.save()
        self.assertTrue(self.user.profile.is_trustworthy())

    def test_user_trustworthy_when_has_posts(self):
        self.assertFalse(self.user.profile.is_trustworthy())
        self.user.profile.num_posts = 6
        self.user.profile.save()
        self.assertTrue(self.user.profile.is_trustworthy())

    def test_user_trustworthy_when_is_staff(self):
        self.assertFalse(self.user.profile.is_trustworthy())
        self.user.is_staff = True
        self.user.profile.save()
        self.assertTrue(self.user.profile.is_trustworthy())

    def test_user_trustworthy_when_is_superuser(self):
        self.assertFalse(self.user.profile.is_trustworthy())
        self.user.is_superuser = True
        self.user.profile.save()
        self.assertTrue(self.user.profile.is_trustworthy())


class ProfileEnabledEmailTypes(TestCase):
    """
    Test the get_enabled_email_types method of Profile model
    """

    fixtures = ['email_preference_type']

    def test_get_enabled_email_types(self):
        user = User.objects.create_user("testuser")

        # Defaults (all email types with sent_by_default=True should be enabled)
        default_email_types = user.profile.get_enabled_email_types()
        self.assertEqual(len(default_email_types), EmailPreferenceType.objects.filter(send_by_default=True).count())

        # Disable email preferences which are set to true by default
        # At each iteraiton of the foorloop, one less email type should be returned by get_enabled_email_types
        for count, email_type in enumerate(EmailPreferenceType.objects.filter(send_by_default=True)):
            UserEmailSetting.objects.create(user=user, email_type=email_type)
            email_types = user.profile.get_enabled_email_types()
            self.assertEqual(len(email_types), len(default_email_types) - (count + 1))

        # Test adding email types which are not sent by default adds them to the result of get_enabled_email_types
        # Because at the start of the loop there are no email types enabled, at each iteration of the loop the
        # list returned by get_enabled_email_types should be increased by one element
        for count, email_type in enumerate(EmailPreferenceType.objects.filter(send_by_default=False)):
            UserEmailSetting.objects.create(user=user, email_type=email_type)
            email_types = user.profile.get_enabled_email_types()
            self.assertEqual(len(email_types), count + 1)


class ProfileTestDownloadCountFields(TestCase):

    fixtures = ['licenses']

    def setUp(self):
        self.user, self.packs, self.sounds = create_user_and_sounds(num_sounds=3, num_packs=3,
                                                     processing_state="OK", moderation_state="OK")

    @mock.patch('sounds.models.delete_sound_from_gaia')
    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_download_sound_count_field_is_updated(self, delete_sounds_from_search_engine, delete_sound_from_gaia):
        # Test downloading sounds increases the "num_sound_downloads" field
        for i in range(0, len(self.sounds)):
            Download.objects.create(user=self.user, sound=self.sounds[i], license_id=self.sounds[i].license_id)
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_sound_downloads, i + 1)
            self.assertEqual(self.sounds[0].user.profile.num_user_sounds_downloads, i + 1)

        # Test deleting downloaded sounds decreases the "num_sound_downloads" field
        # Delete 2 of the 3 downloaded sounds
        for i in range(0, len(self.sounds) - 1):
            self.sounds[i].delete()  # This should decrease "num_sound_downloads" field
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_sound_downloads, len(self.sounds) - 1 - i)
            self.assertEqual(self.sounds[0].user.profile.num_user_sounds_downloads, len(self.sounds) - 1 - i)

        # Now test that if the "num_sound_downloads" field is out of sync and deleting a sound would set it to
        # -1, we will set it to 0 instead to avoid DB check constraint error
        self.user.profile.num_sound_downloads = 0  # Set num_sound_downloads out of sync (should be 1 instead of 0)
        self.user.profile.save()
        self.sounds[2].delete()  # Delete the remaining sound
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.num_sound_downloads, 0)
        self.assertEqual(self.sounds[2].user.profile.num_user_sounds_downloads, 0)

    def test_download_pack_count_field_is_updated(self):
        # Test downloading packs increases the "num_pack_downloads" field
        for i in range(0, len(self.packs)):
            PackDownload.objects.create(user=self.user, pack=self.packs[i])
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_pack_downloads, i + 1)
            self.assertEqual(self.packs[i].user.profile.num_user_packs_downloads, i + 1)

        # Test deleting downloaded packs decreases the "num_pack_downloads" field
        # Delete 2 of the 3 downloaded packs
        for i in range(0, len(self.packs) - 1):
            self.packs[i].delete()  # This should decrease "num_sound_downloads" field
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_pack_downloads, len(self.packs) - 1 - i)
            self.assertEqual(self.packs[i].user.profile.num_user_packs_downloads, len(self.packs) - 1 - i)

        # Now test that if the "num_pack_downloads" field is out of sync and deleting a pack would set it to
        # -1, we will set it to 0 instead to avoid DB check constraint error
        self.user.profile.num_pack_downloads = 0  # Set num_sound_downloads out of sync (should be 1 instead of 0)
        self.user.profile.save()
        self.packs[2].delete()  # Delete the remaining sound
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.num_pack_downloads, 0)
        self.assertEqual(self.packs[2].user.profile.num_user_packs_downloads, 0)
