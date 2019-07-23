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

import freezegun
import mock
from dateutil.parser import parse as parse_date
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

import accounts.models
from accounts.management.commands.process_email_bounces import process_message, decode_idna_email
from accounts.models import EmailPreferenceType, EmailBounce
from accounts.views import handle_uploaded_image
from forum.models import Forum, Thread, Post
from sounds.models import Pack
from tags.models import TaggedItem
from utils.mail import send_mail
from utils.test_helpers import override_avatars_path_with_temp_directory


class ProfileGetUserTags(TestCase):
    fixtures = ['licenses', 'sounds_with_tags']

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
        tag_names = [item["name"] for item in list(user.profile.get_user_tags())]
        used_tag_names = list(set([item.tag.name for item in TaggedItem.objects.filter(user=user)]))
        non_used_tag_names = list(set([item.tag.name for item in TaggedItem.objects.exclude(user=user)]))

        # Test that tags retrieved with get_user_tags are those found in db
        self.assertEqual(len(set(tag_names).intersection(used_tag_names)), len(tag_names))
        self.assertEqual(len(set(tag_names).intersection(non_used_tag_names)), 0)

        # Test solr not available return False
        conf = {'select.side_effect': Exception}
        mock_solr.return_value.configure_mock(**conf)
        self.assertEqual(user.profile.get_user_tags(), False)


class UserEditProfile(TestCase):
    fixtures = ['email_preference_type']

    @override_avatars_path_with_temp_directory
    def test_handle_uploaded_image(self):
        user = User.objects.create_user("testuser")
        f = InMemoryUploadedFile(open(settings.MEDIA_ROOT + '/images/70x70_avatar.png'), None, None, None, None, None)
        handle_uploaded_image(user.profile, f)

        # Test that avatar files were created
        self.assertEqual(os.path.exists(user.profile.locations("avatar.S.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.M.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.L.path")), True)

    def test_edit_user_profile(self):
        user = User.objects.create_user("testuser")
        self.client.force_login(user)
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
        encoded_email = u'user@xn--eb-tbv.de'
        decoded_email = u'user@\u2211eb.de'
        self.assertEqual(decoded_email, decode_idna_email(encoded_email))


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
        created = parse_date("2019-02-03 10:50:00")
        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()
        with freezegun.freeze_time("2019-02-03 10:52:30"):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertFalse(can_post)
            self.assertIn("was less than 5", reason)

        with freezegun.freeze_time("2019-02-03 11:03:30"):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertTrue(can_post)

    def test_can_post_in_forum_has_sounds(self):
        """If you have sounds you can post even within 5 minutes of the last one"""
        created = parse_date("2019-02-03 10:50:00")
        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()
        self.user.profile.num_sounds = 3
        self.user.profile.save()

        with freezegun.freeze_time("2019-02-03 10:52:30"):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertTrue(can_post)

    def test_can_post_in_forum_numposts(self):
        """If you have no sounds, you can't post more than x posts per day.
        this is 5 + d^2 posts, where d is the number of days between your first post and now"""
        # our first post, 2 days ago
        created = parse_date("2019-02-03 10:50:00")

        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()

        # 2 days later, the maximum number of posts we can make today will be 5 + 4 = 9
        today = parse_date("2019-02-05 01:50:00")
        for i in range(9):
            post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
            today = today + datetime.timedelta(minutes=i+10)
            post.created = today
            post.save()

        # After making 9 posts, we can't make any more
        with freezegun.freeze_time("2019-02-05 14:52:30"):
            can_post, reason = self.user.profile.can_post_in_forum()
            self.assertFalse(can_post)
            self.assertIn("you exceeded your maximum", reason)

    def test_can_post_in_forum_admin(self):
        """If you're a forum admin, you can post even if you have no sounds, you're within
        5 minutes of the last one, and you've gone over the limit of posts for the day"""
        created = parse_date("2019-02-03 10:50:00")
        post = Post.objects.create(thread=self.thread, body="", author=self.user, moderation_state="OK")
        post.created = created
        post.save()
        perm = Permission.objects.get_by_natural_key('can_moderate_forum', 'forum', 'post')
        self.user.user_permissions.add(perm)

        with freezegun.freeze_time("2019-02-04 10:00:30"):
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
