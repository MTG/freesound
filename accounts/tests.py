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

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.test.utils import override_settings, skipIf
from django.contrib.auth.models import User, Permission
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.sites.models import Site
from django.urls import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.core.management import call_command
from django.core import mail
from django.conf import settings
from accounts.models import Profile, EmailPreferenceType, SameUser, ResetEmailRequest, OldUsername, EmailBounce, UserFlag
from accounts.views import handle_uploaded_image
from accounts.forms import FsPasswordResetForm, DeleteUserForm, UsernameField, RegistrationForm
from accounts.management.commands.process_email_bounces import decode_idna_email
from sounds.models import License, Sound, Pack, DeletedSound, SoundOfTheDay, BulkUploadProgress
from tags.models import TaggedItem
from utils.filesystem import File
from tags.models import Tag
from comments.models import Comment
from forum.models import Thread, Post, Forum
from messages.models import Message, MessageBody
from tickets.models import Ticket
from utils.mail import transform_unique_email, send_mail
import accounts.models
import mock
import os
import tempfile
import shutil
import datetime
import json


class SimpleUserTest(TestCase):

    fixtures = ['users', 'sounds_with_tags']

    def setUp(self):
        self.user = User.objects.all()[0]
        self.sound = Sound.objects.all()[0]
        SoundOfTheDay.objects.create(sound=self.sound, date_display=datetime.date.today())

    def test_account_response_ok(self):
        # 200 response on account access
        resp = self.client.get(reverse('account', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_sounds_response_ok(self):
        # 200 response on user sounds access
        resp = self.client.get(reverse('sounds-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_flag_response_ok(self):
        # 200 response on user flag and clear flag access
        self.user.set_password('12345')
        self.user.is_superuser = True
        self.user.save()
        a =self.client.login(username=self.user.username, password='12345')
        resp = self.client.get(reverse('flag-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('clear-flags-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_comments_response_ok(self):
        # 200 response on user comments and comments for user access
        resp = self.client.get(reverse('comments-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('comments-by-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_geotags_response_ok(self):
        # 200 response on user geotags access
        resp = self.client.get(reverse('geotags-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_packs_response_ok(self):
        # 200 response on user packs access
        resp = self.client.get(reverse('packs-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_downloaded_response_ok(self):
        # 200 response on user downloaded sounds and packs access
        resp = self.client.get(reverse('user-downloaded-sounds', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('user-downloaded-packs', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_bookmarks_response_ok(self):
        # 200 response on user bookmarks sounds and packs access
        resp = self.client.get(reverse('bookmarks-for-user', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    def test_user_follow_response_ok(self):
        # 200 response on user user bookmarks sounds and packs access
        resp = self.client.get(reverse('user-following-users', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('user-followers', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('user-following-tags', kwargs={'username': self.user.username}))
        self.assertEqual(resp.status_code, 200)

    @mock.patch('gearman.GearmanClient.submit_job')
    def test_sounds_response_ok(self, submit_job):
        # 200 response on sounds page access
        resp = self.client.get(reverse('sounds'))
        self.assertEqual(resp.status_code, 200)

        self.sound.moderation_state="OK"
        self.sound.processing_state="OK"
        self.sound.save()
        user = self.sound.user
        user.set_password('12345')
        user.is_superuser = True
        user.save()
        self.client.login(username=user.username, password='12345')
        resp = self.client.get(reverse('sound', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-flag', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-edit-sources', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-edit', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-geotag', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-delete', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-similar', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('sound-downloaders', kwargs={'username': user.username, "sound_id": self.sound.id}))
        self.assertEqual(resp.status_code, 200)

    def test_tags_response_ok(self):
        # 200 response on tags page access
        resp = self.client.get(reverse('tags'))
        self.assertEqual(resp.status_code, 200)

    def test_packs_response_ok(self):
        # 200 response on packs page access
        resp = self.client.get(reverse('packs'))
        self.assertEqual(resp.status_code, 200)

    def test_comments_response_ok(self):
        # 200 response on comments page access
        resp = self.client.get(reverse('comments'))
        self.assertEqual(resp.status_code, 200)

    def test_remixed_response_ok(self):
        # 200 response on remixed sounds page access
        resp = self.client.get(reverse('remix-groups'))
        self.assertEqual(resp.status_code, 200)

    def test_contact_response_ok(self):
        # 200 response on contact page access
        resp = self.client.get(reverse('contact'))
        self.assertEqual(resp.status_code, 200)

    def test_sound_search_response_ok(self):
        # 200 response on sound search page access
        resp = self.client.get(reverse('sounds-search'))
        self.assertEqual(resp.status_code, 200)

    def test_geotags_box_response_ok(self):
        # 200 response on geotag box page access
        resp = self.client.get(reverse('geotags-box'))
        self.assertEqual(resp.status_code, 200)

    def test_geotags_box_iframe_response_ok(self):
        # 200 response on geotag box iframe
        resp = self.client.get(reverse('embed-geotags-box-iframe'))
        self.assertEqual(resp.status_code, 200)

    def test_accounts_manage_pages(self):
        # 200 response on Account registration page
        resp = self.client.get(reverse('accounts-register'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account reactivation page
        resp = self.client.get(reverse('accounts-resend-activation'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account username reminder page
        resp = self.client.get(reverse('accounts-username-reminder'))
        self.assertEqual(resp.status_code, 200)

        # Login user with moderation permissions
        user = User.objects.create_user("testuser", password="testpass")
        ct = ContentType.objects.get_for_model(Ticket)
        p = Permission.objects.get(content_type=ct, codename='can_moderate')
        ct2 = ContentType.objects.get_for_model(Post)
        p2 = Permission.objects.get(content_type=ct2, codename='can_moderate_forum')
        user.user_permissions.add(p, p2)
        self.client.login(username='testuser', password='testpass')

        # 200 response on TOS acceptance page
        resp = self.client.get(reverse('tos-acceptance'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account email reset page
        resp = self.client.get(reverse('accounts-email-reset'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account home page
        resp = self.client.get(reverse('accounts-home'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account edit page
        resp = self.client.get(reverse('accounts-edit'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account edit email settings page
        resp = self.client.get(reverse('accounts-email-settings'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account attribution page
        resp = self.client.get(reverse('accounts-attribution'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account stream page
        resp = self.client.get(reverse('stream'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account messages page
        resp = self.client.get(reverse('messages'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account archived messages page
        resp = self.client.get(reverse('messages-archived'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account sent messages page
        resp = self.client.get(reverse('messages-sent'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account new message page
        resp = self.client.get(reverse('messages-new'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on Account permissions granted page
        resp = self.client.get(reverse('access-tokens'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on ticket moderation page
        resp = self.client.get(reverse('tickets-moderation-home'))
        self.assertEqual(resp.status_code, 200)

        # 200 response on wiki page
        resp = self.client.get(reverse('wiki'))
        self.assertEqual(resp.status_code, 302)

        # 200 response on forums moderation page
        resp = self.client.get(reverse('forums-moderate'))
        self.assertEqual(resp.status_code, 200)

    def test_username_check(self):
        username = 'test_user_new'
        resp = self.client.get(reverse('check_username'),
                {'username': username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], True)

        user = User.objects.create_user(username, password="testpass")
        resp = self.client.get(reverse('check_username'),
                {'username': username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        # Now we change the username and we check that both old and new usernames are not valid
        user.username = 'other_username'
        user.save()

        # First we check that the OldUsername object is created
        self.assertEqual(OldUsername.objects.filter(username=username, user=user).count(), 1)

        resp = self.client.get(reverse('check_username'),
                {'username': username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)

        resp = self.client.get(reverse('check_username'),
                {'username': user.username})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], False)


class OldUserLinksRedirect(TestCase):

    fixtures = ['users']

    def setUp(self):
        self.user = User.objects.all()[0]

    def test_old_user_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        resp = self.client.get(reverse('old-account-page'), data={'id': self.user.id})
        self.assertEqual(resp.status_code, 301)

    def test_old_user_link_redirect_not_exists_id(self):
        # 404 id does not exist (user with id 999 does not exist in fixture)
        resp = self.client.get(reverse('old-account-page'), data={'id': 999}, follow=True)
        self.assertEqual(resp.status_code, 404)

    def test_old_user_link_redirect_invalid_id(self):
        # 404 invalid id
        resp = self.client.get(reverse('old-account-page'), data={'id': 'invalid_id'}, follow=True)
        self.assertEqual(resp.status_code, 404)


class UserRegistrationAndActivation(TestCase):

    fixtures = ['users']

    def test_user_save(self):
        u = User.objects.create_user("testuser2", password="testpass")
        self.assertEqual(Profile.objects.filter(user=u).exists(), True)
        u.save()  # Check saving user again (with existing profile) does not fail

    @override_settings(RECAPTCHA_PUBLIC_KEY='')
    def test_user_registration(self):
        username = 'new_user'

        # Try registration without accepting tos
        resp = self.client.post(reverse('accounts-register'), data={
            u'username': [username],
            u'password1': [u'123456'],
            u'accepted_tos': [u''],
            u'email1': [u'example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('You must accept the terms of use', resp.content)
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try registration with bad email
        resp = self.client.post(reverse('accounts-register'), data={
            u'username': [username],
            u'password1': [u'123456'],
            u'accepted_tos': [u'on'],
            u'email1': [u'exampleemail.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Enter a valid email', resp.content)
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try registration with no username
        resp = self.client.post(reverse('accounts-register'), data={
            u'username': [''],
            u'password1': [u'123456'],
            u'accepted_tos': [u'on'],
            u'email1': [u'example@email.com.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('This field is required', resp.content)
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try successful registration
        resp = self.client.post(reverse('accounts-register'), data={
            u'username': [username],
            u'password1': [u'123456'],
            u'accepted_tos': [u'on'],
            u'email1': [u'example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Registration done, activate your account', resp.content)
        self.assertEqual(User.objects.filter(username=username).count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # An email was sent!
        self.assertEqual(mail.outbox[0].subject, "[freesound] activation link.")

        # Try register again with same username
        resp = self.client.post(reverse('accounts-register'), data={
            u'username': [username],
            u'password1': [u'123456'],
            u'accepted_tos': [u'on'],
            u'email1': [u'example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('A user with that username already exists', resp.content)
        self.assertEqual(User.objects.filter(username=username).count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # No new email sent

        # Try with repeated email address
        resp = self.client.post(reverse('accounts-register'), data={
            u'username': ['a_different_username'],
            u'password1': [u'123456'],
            u'accepted_tos': [u'on'],
            u'email1': [u'example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn('A user using that email address already exists', resp.content)
        self.assertEqual(User.objects.filter(username=username).count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # No new email sent

    def test_user_activation(self):
        user = User.objects.get(username="User6Inactive")  # Inactive user in fixture

        # Test calling accounts-activate with wrong hash, user should not be activated
        bad_hash = '4dad3dft'
        resp = self.client.get(reverse('accounts-activate', args=[user.username, bad_hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['decode_error'], True)
        self.assertEqual(User.objects.get(username="User6Inactive").is_active, False)

        # Test calling accounts-activate with good hash, user should be activated
        from utils.encryption import create_hash
        good_hash = create_hash(user.id)
        resp = self.client.get(reverse('accounts-activate', args=[user.username, good_hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['all_ok'], True)
        self.assertEqual(User.objects.get(username="User6Inactive").is_active, True)

        # Test calling accounts-activate for a user that does not exist
        resp = self.client.get(reverse('accounts-activate', args=["noone", hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['user_does_not_exist'], True)


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

    @override_settings(AVATARS_PATH=tempfile.mkdtemp())
    def test_handle_uploaded_image(self):
        user = User.objects.create_user("testuser", password="testpass")
        f = InMemoryUploadedFile(open(settings.MEDIA_ROOT + '/images/70x70_avatar.png'), None, None, None, None, None)
        handle_uploaded_image(user.profile, f)

        # Test that avatar files were created
        self.assertEqual(os.path.exists(user.profile.locations("avatar.S.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.M.path")), True)
        self.assertEqual(os.path.exists(user.profile.locations("avatar.L.path")), True)

        # Delete tmp directory
        shutil.rmtree(settings.AVATARS_PATH)

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
            self.assertEqual(user.old_usernames.count(), i+1)

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

    @override_settings(AVATARS_PATH=tempfile.mkdtemp())
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

        # Delete tmp directory
        shutil.rmtree(settings.AVATARS_PATH)


class UserUploadAndDescribeSounds(TestCase):

    fixtures = ['initial_data']

    @skipIf(True, "Test not ready for new uploader")
    @override_settings(UPLOADS_PATH=tempfile.mkdtemp())
    def test_handle_uploaded_file_html(self):
        # TODO: test html5 file uploads when we change uploader
        user = User.objects.create_user("testuser", password="testpass")
        self.client.login(username='testuser', password='testpass')

        # Test successful file upload
        filename = "file.wav"
        f = SimpleUploadedFile(filename, "file_content")
        resp = self.client.post("/home/upload/html/", {'file': f})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os.path.exists(settings.UPLOADS_PATH + '/%i/%s' % (user.id, filename)), True)

        # Test file upload that should fail
        filename = "file.xyz"
        f = SimpleUploadedFile(filename, "file_content")
        resp = self.client.post("/home/upload/html/", {'file': f})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os.path.exists(settings.UPLOADS_PATH + '/%i/%s' % (user.id, filename)), False)

        # Delete tmp directory
        shutil.rmtree(settings.UPLOADS_PATH)

    @override_settings(UPLOADS_PATH=tempfile.mkdtemp())
    def test_select_uploaded_files_to_describe(self):
        # Create audio files
        filenames = ['file1.wav', 'file2.wav', 'file3.wav']
        user = User.objects.create_user("testuser", password="testpass")
        self.client.login(username='testuser', password='testpass')
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.mkdir(user_upload_path)
        for filename in filenames:
            f = open(user_upload_path + filename, 'a')
            f.write(os.urandom(1024))  # Add random content to the file to avoid equal md5
            f.close()

        # Check that files are displayed in the template
        resp = self.client.get('/home/describe/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['file_structure'].children), len(filenames))

        # Selecting one file redirects to /home/describe/sounds/
        resp = self.client.post('/home/describe/', {
            'describe': [u'Describe selected files'],
            'sound-files': [u'file1'],
        })
        self.assertRedirects(resp, '/home/describe/sounds/')

        # Selecting multiple file redirects to /home/describe/license/
        resp = self.client.post('/home/describe/', {
            'describe': [u'Describe selected files'],
            'sound-files': [u'file1', u'file0'],
        })
        self.assertRedirects(resp, '/home/describe/license/')

        # Selecting files to delete, redirecte to delete confirmation
        filenames_to_delete = [u'file1', u'file0']
        resp = self.client.post('/home/describe/', {
            'delete': [u'Delete selected files'],
            'sound-files': filenames_to_delete,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['filenames']), len(filenames_to_delete))

        # Selecting confirmation of files to delete
        resp = self.client.post('/home/describe/', {
            'delete_confirm': [u'delete_confirm'],
            'sound-files': filenames_to_delete,
        })
        self.assertRedirects(resp, '/home/describe/')
        self.assertEqual(len(os.listdir(user_upload_path)), len(filenames) - len(filenames_to_delete))

        # Delete tmp directory
        shutil.rmtree(settings.UPLOADS_PATH)

    @override_settings(UPLOADS_PATH=tempfile.mkdtemp())
    def test_describe_selected_files(self):
        # Create audio files
        filenames = ['file1.wav', 'file2.wav']
        user = User.objects.create_user("testuser", password="testpass")
        self.client.login(username='testuser', password='testpass')
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.mkdir(user_upload_path)
        for filename in filenames:
            f = open(user_upload_path + filename, 'a')
            f.write(os.urandom(1024))  # Add random content to the file to avoid equal md5
            f.close()

        # Set license and pack data in session
        session = self.client.session
        session['describe_license'] = License.objects.all()[0]
        session['describe_pack'] = False
        session['describe_sounds'] = [File(1, filenames[0], user_upload_path + filenames[0], False),
                                      File(2, filenames[1], user_upload_path + filenames[1], False)]
        session.save()

        # Post description information
        resp = self.client.post('/home/describe/sounds/', {
            'submit': [u'Submit and continue'],
            '0-lat': [u'46.31658418182218'],
            '0-lon': [u'3.515625'],
            '0-zoom': [u'16'],
            '0-tags': [u'testtag1 testtag2 testtag3'],
            '0-pack': [u''],
            '0-license': [u'3'],
            '0-description': [u'a test description for the sound file'],
            '0-new_pack': [u''],
            '0-name': [u'%s' % filenames[0]],
            '1-license': [u'3'],
            '1-description': [u'another test description'],
            '1-lat': [u''],
            '1-pack': [u''],
            '1-lon': [u''],
            '1-name': [u'%s' % filenames[1]],
            '1-new_pack': [u'Name of a new pack'],
            '1-zoom': [u''],
            '1-tags': [u'testtag1 testtag4 testtag5'],
        })

        # Check that post redirected to first describe page with confirmation message on sounds described
        self.assertRedirects(resp, '/home/describe/')
        self.assertEqual('You have described all the selected files' in resp.cookies['messages'].value, True)

        # Check that sounds have been created along with related tags, geotags and packs
        self.assertEqual(user.sounds.all().count(), 2)
        self.assertEqual(Pack.objects.filter(name='Name of a new pack').exists(), True)
        self.assertEqual(Tag.objects.filter(name__contains="testtag").count(), 5)
        self.assertNotEqual(user.sounds.get(original_filename=filenames[0]).geotag, None)


class UserDelete(TestCase):

    fixtures = ['sounds']

    def create_user_and_content(self, is_index_dirty=True):
        user = User.objects.create_user("testuser", password="testpass")
        # Create comments
        target_sound = Sound.objects.all()[0]
        for i in range(0, 3):
            target_sound.add_comment(user, "Comment %i" % i)
        # Create threads and posts
        thread = Thread.objects.create(author=user, title="Test thread", forum=Forum.objects.create(name="Test forum"))
        for i in range(0, 3):
            Post.objects.create(author=user, thread=thread, body="Post %i body" % i)
        # Create sounds and packs
        pack = Pack.objects.create(user=user, name="Test pack")
        for i in range(0, 3):
            Sound.objects.create(user=user,
                                 original_filename="Test sound %i" % i,
                                 pack=pack,
                                 is_index_dirty=is_index_dirty,
                                 license=License.objects.all()[0],
                                 md5="fakemd5%i" % i,
                                 moderation_state="OK",
                                 processing_state="OK")
        return user

    def test_user_delete_make_invalid_password(self):
        user = self.create_user_and_content(is_index_dirty=False)
        user.profile.delete_user()
        self.assertFalse(user.has_usable_password())

    def test_user_delete_keep_sounds(self):
        # This should set user's attribute active to false and anonymize it
        user = self.create_user_and_content(is_index_dirty=False)
        user.profile.delete_user()
        self.assertEqual(User.objects.get(id=user.id).profile.is_deleted_user, True)

        self.assertEqual(user.username, "deleted_user_%s" % user.id)
        self.assertEqual(user.profile.about, '')
        self.assertEqual(user.profile.home_page, '')
        self.assertEqual(user.profile.signature, '')
        self.assertEqual(user.profile.geotag, None)

        self.assertEqual(Comment.objects.filter(user__id=user.id).exists(), True)
        self.assertEqual(Thread.objects.filter(author__id=user.id).exists(), True)
        self.assertEqual(Post.objects.filter(author__id=user.id).exists(), True)
        self.assertEqual(DeletedSound.objects.filter(user__id=user.id).exists(), False)
        self.assertEqual(Pack.objects.filter(user__id=user.id).exists(), True)
        self.assertEqual(Sound.objects.filter(user__id=user.id).exists(), True)
        self.assertEqual(Sound.objects.filter(user__id=user.id)[0].is_index_dirty, True)

    @mock.patch('sounds.models.delete_sound_from_solr')
    def test_user_delete_remove_sounds(self, delete_sound_solr):
        # This should set user's attribute deleted_user to True and anonymize it,
        # also should remove users Sounds and Packs, and create DeletedSound
        # objects
        user = self.create_user_and_content()
        user_sounds = Sound.objects.filter(user=user)
        user_sound_ids = [s.id for s in user_sounds]
        user.profile.delete_user(remove_sounds=True)
        self.assertEqual(User.objects.get(id=user.id).profile.is_deleted_user, True)
        self.assertEqual(user.username, "deleted_user_%s" % user.id)
        self.assertEqual(user.profile.about, '')
        self.assertEqual(user.profile.home_page, '')
        self.assertEqual(user.profile.signature, '')
        self.assertEqual(user.profile.geotag, None)

        self.assertEqual(Comment.objects.filter(user__id=user.id).exists(), True)
        self.assertEqual(Thread.objects.filter(author__id=user.id).exists(), True)
        self.assertEqual(Post.objects.filter(author__id=user.id).exists(), True)
        self.assertEqual(Pack.objects.filter(user__id=user.id).exists(), True)
        self.assertEqual(Pack.objects.filter(user__id=user.id).all()[0].is_deleted, True)
        self.assertEqual(Sound.objects.filter(user__id=user.id).exists(), False)
        self.assertEqual(DeletedSound.objects.filter(user__id=user.id).exists(), True)

        calls = [mock.call(i) for i in user_sound_ids]
        delete_sound_solr.assert_has_calls(calls, any_order=True)

    def test_user_delete_using_form(self):
        # This should set user's attribute active to false and anonymize it
        user = self.create_user_and_content(is_index_dirty=False)
        a = self.client.login(username=user.username, password='testpass')
        form = DeleteUserForm(user_id=user.id)
        encr_link = form.initial['encrypted_link']
        resp = self.client.post(reverse('accounts-delete'),
                {'encrypted_link': encr_link, 'password': 'testpass', 'delete_sounds': 'delete_sounds'})

        self.assertEqual(User.objects.get(id=user.id).profile.is_deleted_user, True)

    def test_fail_user_delete_using_form(self):
        # This should try to delete the account but with a wrong password
        user = self.create_user_and_content(is_index_dirty=False)
        a = self.client.login(username=user.username, password='testpass')
        form = DeleteUserForm(user_id=user.id)
        encr_link = form.initial['encrypted_link']
        resp = self.client.post(reverse('accounts-delete'),
                {'encrypted_link': encr_link, 'password': 'wrong_pass', 'delete_sounds': 'delete_sounds'})

        self.assertEqual(User.objects.get(id=user.id).profile.is_deleted_user, False)


class UserEmailsUniqueTestCase(TestCase):

    def setUp(self):
        self.user_a = User.objects.create_user("user_a", password="12345", email='a@b.com')
        self.original_shared_email = 'c@d.com'
        self.user_b = User.objects.create_user("user_b", password="12345", email=self.original_shared_email)
        self.user_c = User.objects.create_user("user_c", password="12345",
                                               email=transform_unique_email(self.original_shared_email))
        SameUser.objects.create(
            main_user=self.user_b,
            main_orig_email=self.user_b.email,
            secondary_user=self.user_c,
            secondary_orig_email=self.user_b.email,  # Must be same email (original)
        )
        # User a never had problems with email
        # User b and c had the same email, but user_c's was automaitcally changed to avoid duplicates

    def test_redirects_when_shared_emails(self):

        # Try to log-in with user and go to messages page (any login_required page would work)
        # User a is not in same users table, so redirect should be plain and simple to messages
        # NOTE: in the following tests we don't use `self.client.login` because what we want to test
        # is in fact in the login view logic.
        resp = self.client.post(reverse('login'),
                                {'username': self.user_a, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

        resp = self.client.get(reverse('logout'))
        # Now try with user_b and user_c. User b had a shared email with user_c. Even if user_b's email was
        # not changed, he is still redirected to the duplicate email cleanup page
        resp = self.client.post(reverse('login'),
                                {'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('accounts-multi-email-cleanup') + '?next=%s' % reverse('messages'))
        resp = self.client.get(reverse('logout'))
        resp = self.client.post(reverse('login'),
                                {'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('accounts-multi-email-cleanup') + '?next=%s' % reverse('messages'))

    def test_fix_email_issues_with_secondary_user_email_change(self):
        # user_c changes his email and tries to login, redirect should go to email cleanup page and from there
        # directly to messages (2 redirect steps)
        self.user_c.email = 'new@email.com'  # Must be different than transform_unique_email('c@d.com')
        self.user_c.save()
        resp = self.client.post(reverse('login'), follow=True,
                                data={'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertEquals(resp.redirect_chain[0][0],
                          reverse('accounts-multi-email-cleanup') + '?next=%s' % reverse('messages'))
        self.assertEquals(resp.redirect_chain[1][0], reverse('messages'))

        # Also check that related SameUser objects have been removed
        self.assertEquals(SameUser.objects.all().count(), 0)

        resp = self.client.get(reverse('logout'))
        # Now next time user_c tries to go to messages again, there is only one redirect (like for user_a)
        resp = self.client.post(reverse('login'),
                                {'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

        resp = self.client.get(reverse('logout'))
        # Also if user_b logs in, redirect goes straight to messages
        resp = self.client.post(reverse('login'),
                                {'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

    def test_fix_email_issues_with_main_user_email_change(self):
        # user_b changes his email and tries to login, redirect should go to email cleanup page and from there
        # directly to messages (2 redirect steps). Also user_c email should be changed to the original email of
        # both users
        self.user_b.email = 'new@email.com'  # Must be different than transform_unique_email('c@d.com')
        self.user_b.save()
        resp = self.client.post(reverse('login'), follow=True,
                                data={'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertEquals(resp.redirect_chain[0][0],
                          reverse('accounts-multi-email-cleanup') + '?next=%s' % reverse('messages'))
        self.assertEquals(resp.redirect_chain[1][0], reverse('messages'))

        # Check that user_c email was changed
        self.user_c = User.objects.get(id=self.user_c.id)  # Reload user from db
        self.assertEquals(self.user_c.email, self.original_shared_email)

        # Also check that related SameUser objects have been removed
        self.assertEquals(SameUser.objects.all().count(), 0)

        resp = self.client.get(reverse('logout'))
        # Now next time user_b tries to go to messages again, there is only one redirect (like for user_a)
        resp = self.client.post(reverse('login'),
                                {'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

        resp = self.client.get(reverse('logout'))
        # Also if user_c logs in, redirect goes straight to messages
        resp = self.client.post(reverse('login'),
                                {'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

    def test_fix_email_issues_with_both_users_email_change(self):
        # If both users have changed email, we should make sure that user_c email is not overwritten before
        # SameUser object is deleted
        self.user_b.email = 'new@email.com'
        self.user_b.save()
        self.user_c.email = 'new2w@email.com'
        self.user_c.save()
        resp = self.client.post(reverse('login'), follow=True,
                                data={'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertEquals(resp.redirect_chain[0][0],
                          reverse('accounts-multi-email-cleanup') + '?next=%s' % reverse('messages'))
        self.assertEquals(resp.redirect_chain[1][0], reverse('messages'))

        # Check that user_c email was not changed
        self.user_c = User.objects.get(id=self.user_c.id)  # Reload user from db
        self.assertEquals(self.user_c.email, 'new2w@email.com')

        # Also check that related SameUser objects have been removed
        self.assertEquals(SameUser.objects.all().count(), 0)

        resp = self.client.get(reverse('logout'))
        # Now next time user_b tries to go to messages again, there is only one redirect (like for user_a)
        resp = self.client.post(reverse('login'),
                                {'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

        resp = self.client.get(reverse('logout'))
        # Also if user_c logs in, redirect goes straight to messages
        resp = self.client.post(reverse('login'),
                                {'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

    def test_user_profile_get_email(self):
        # Here we test that when we send an email to users that have SameUser objects we chose the right email address

        # user_a has no SameUser objects, emails should be sent directly to his address
        self.assertEquals(self.user_a.profile.get_email_for_delivery(), self.user_a.email)

        # user_b has SameUser with user_c, but user_b is main user so emails should be sent directly to his address
        self.assertEquals(self.user_b.profile.get_email_for_delivery(), self.user_b.email)

        # user_c should get emails at user_b email address (user_b is main user)
        self.assertEquals(self.user_c.profile.get_email_for_delivery(), self.user_b.email)

        # If we remove SameUser entries, email of user_c is sent directly to his address
        SameUser.objects.all().delete()
        self.assertEquals(self.user_c.profile.get_email_for_delivery(), self.user_c.email)


class PasswordReset(TestCase):
    def test_reset_form_get_users(self):
        """Check that a user with an unknown password hash can reset their password"""

        user = User.objects.create_user("testuser", email="testuser@freesound.org")

        # Using Django's password reset form, no user will be returned
        form = PasswordResetForm()
        dj_users = form.get_users("testuser@freesound.org")
        self.assertEqual(len(list(dj_users)), 0)

        # But using our form, a user will be returned
        form = FsPasswordResetForm()
        fs_users = form.get_users("testuser@freesound.org")
        self.assertEqual(list(fs_users)[0].get_username(), user.get_username())

    @override_settings(SITE_ID=2)
    def test_reset_view_with_email(self):
        """Check that the reset password view calls our form"""
        Site.objects.create(id=2, domain="freesound.org", name="Freesound")
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        self.client.post(reverse("password_reset"), {"email_or_username": "testuser@freesound.org"})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Password reset on Freesound")

    @override_settings(SITE_ID=2)
    def test_reset_view_with_username(self):
        """Check that the reset password view calls our form"""
        Site.objects.create(id=2, domain="freesound.org", name="Freesound")
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        self.client.post(reverse("password_reset"), {"email_or_username": "testuser"})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Password reset on Freesound")

    @override_settings(SITE_ID=2)
    def test_reset_view_with_long_username(self):
        """Check that the reset password fails with long username"""
        Site.objects.create(id=2, domain="freesound.org", name="Freesound")
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        long_mail = ('1' * 255) + '@freesound.org'
        resp = self.client.post(reverse("password_reset"), {"email_or_username": long_mail})

        self.assertNotEqual(resp.context['form'].errors, None)


class EmailResetTestCase(TestCase):
    def test_reset_email_form(self):
        """ Check that reset email with the right parameters """
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        user.set_password('12345')
        user.save()
        a = self.client.login(username=user.username, password='12345')
        resp = self.client.post(reverse('accounts-email-reset'), {
            'email': u'new_email@freesound.org',
            'password': '12345',
        })
        self.assertRedirects(resp, reverse('accounts-email-reset-done'))
        self.assertEqual(ResetEmailRequest.objects.filter(user=user, email="new_email@freesound.org").count(), 1)

    def test_reset_email_form_existing_email(self):
        """ Check that reset email with an existing email address """
        user = User.objects.create_user("new_user", email="new_email@freesound.org")
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        user.set_password('12345')
        user.save()
        a = self.client.login(username=user.username, password='12345')
        resp = self.client.post(reverse('accounts-email-reset'), {
            'email': u'new_email@freesound.org',
            'password': '12345',
        })
        self.assertRedirects(resp, reverse('accounts-email-reset-done'))
        self.assertEqual(ResetEmailRequest.objects.filter(user=user, email="new_email@freesound.org").count(), 0)

    def test_reset_long_email(self):
        """ Check reset email with a long email address """
        long_mail = ('1' * 255) + '@freesound.org'
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        user.set_password('12345')
        user.save()
        a = self.client.login(username=user.username, password='12345')
        resp = self.client.post(reverse('accounts-email-reset'), {
            'email': long_mail,
            'password': '12345',
        })

        self.assertNotEqual(resp.context['form'].errors, None)


class ReSendActivationTestCase(TestCase):
    def test_resend_activation_code_from_email(self):
        """
        Check that resend activation code doesn't return an error with post request (use email to identify user)
        """
        user = User.objects.create_user("testuser", email="testuser@freesound.org", is_active=False)
        resp = self.client.post(reverse('accounts-resend-activation'), {
            'user': u'testuser@freesound.org',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check email was sent
        self.assertEqual(mail.outbox[0].subject, u'[freesound] activation link.')

        resp = self.client.post(reverse('accounts-resend-activation'), {
            'user': u'new_email@freesound.org',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check no new email was sent (len() is same as before)

    def test_resend_activation_code_from_username(self):
        """
        Check that resend activation code doesn't return an error with post request (use username to identify user)
        """
        user = User.objects.create_user("testuser", email="testuser@freesound.org", is_active=False)
        resp = self.client.post(reverse('accounts-resend-activation'), {
            'user': u'testuser',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check email was sent
        self.assertEqual(mail.outbox[0].subject, u'[freesound] activation link.')

        resp = self.client.post(reverse('accounts-resend-activation'), {
            'user': u'testuser_does_not_exist',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check no new email was sent (len() is same as before)

    def test_resend_activation_code_from_long_username(self):
        """
        Check that resend activation code returns an error if username is too long
        """
        long_mail = ('1' * 255) + '@freesound.org'
        resp = self.client.post(reverse('accounts-resend-activation'), {
            'user': long_mail,
        })
        self.assertNotEqual(resp.context['form'].errors, None)
        self.assertEqual(len(mail.outbox), 0)  # Check email wasn't sent


class UsernameReminderTestCase(TestCase):
    def test_username_reminder(self):
        """ Check that send username reminder doesn't return an error with post request """
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        resp = self.client.post(reverse('accounts-username-reminder'), {
            'user': u'testuser@freesound.org',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check email was sent
        self.assertEqual(mail.outbox[0].subject, u'[freesound] username reminder.')

        resp = self.client.post(reverse('accounts-username-reminder'), {
            'user': u'new_email@freesound.org',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check no new email was sent (len() is same as before)

    def test_username_reminder_length(self):
        """ Check that send long username reminder return an error with post request """
        long_mail = ('1' * 255) + '@freesound.org'
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        resp = self.client.post(reverse('accounts-username-reminder'), {
            'user': long_mail,
        })
        self.assertNotEqual(resp.context['form'].errors, None)
        self.assertEqual(len(mail.outbox), 0)


class ChangeUsernameTests(TestCase):

    def test_change_username_creates_old_username(self):

        # Create user and check no OldUsername objects exist
        userA = User.objects.create_user('userA', email='userA@freesound.org')
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)

        # Change username and check a OldUsername is created
        userA.username = 'userANewUsername'
        userA.save()
        self.assertEqual(OldUsername.objects.filter(username='userA', user=userA).count(), 1)

        # Save again user and check no new OldUsername are created
        userA.save()
        self.assertEqual(OldUsername.objects.filter(username='userA', user=userA).count(), 1)

        # Change username again and check a new OldUsername has been created
        userA.username = 'userANewNewUsername'
        userA.save()
        self.assertEqual(OldUsername.objects.filter(username='userANewUsername', user=userA).count(), 1)
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Change username back to the previous one (won't be allowed in admin or profile form) and check that a new
        # OldUsername object has been created for the last username
        userA.username = "userANewUsername"
        userA.save()
        self.assertEqual(OldUsername.objects.filter(username='userANewNewUsername', user=userA).count(), 1)
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 3)

        # Change again the username to another previosuly used username and check that no new OldUsername is created
        userA.username = 'userA'
        userA.save()
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 3)

    @override_settings(USERNAME_CHANGE_MAX_TIMES=2)
    def test_change_username_form_profile_page(self):

        # Create user and login
        userA = User.objects.create_user('userA', email='userA@freesound.org', password='testpass')
        self.client.login(username='userA', password='testpass')

        # Test save profile without changing username
        resp = self.client.post(reverse('accounts-edit'), data={u'profile-username': [u'userA']})
        self.assertRedirects(resp, reverse('accounts-home'))  # Successful edit redirects to home
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)

        # Now rename user for the first time
        resp = self.client.post(reverse('accounts-edit'), data={u'profile-username': [u'userANewName']})
        self.assertRedirects(resp, reverse('accounts-home'))  # Successful edit redirects to home
        self.assertEqual(OldUsername.objects.filter(username='userA', user=userA).count(), 1)

        # Now rename user for the second time
        resp = self.client.post(reverse('accounts-edit'), data={u'profile-username': [u'userANewNewName']})
        self.assertRedirects(resp, reverse('accounts-home'))  # Successful edit redirects to home
        self.assertEqual(OldUsername.objects.filter(username='userANewName', user=userA).count(), 1)
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try rename user with an existing username from another user
        userB = User.objects.create_user('userB', email='userB@freesound.org')
        resp = self.client.post(reverse('accounts-edit'), data={u'profile-username': [userB.username]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['profile_form'].has_error('username'), True)  # Error in username field
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try rename user with a username that was already used by the same user in the past
        resp = self.client.post(reverse('accounts-edit'), data={u'profile-username': [u'userA']})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['profile_form'].has_error('username'), True)  # Error in username field
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try to rename for a third time to a valid username but can't rename anymore because exceeded maximum
        # USERNAME_CHANGE_MAX_TIMES (which is set to 2 for this test)
        resp = self.client.post(reverse('accounts-edit'), data={u'profile-username': [u'userANewNewNewName']})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['profile_form'].has_error('username'), True)  # Error in username field
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

    @override_settings(USERNAME_CHANGE_MAX_TIMES=2)
    def test_change_username_form_admin(self):

        User.objects.create_user('superuser', password='testpass', is_superuser=True, is_staff=True)
        self.client.login(username='superuser', password='testpass')

        # Create user and get admin change url
        userA = User.objects.create_user('userA', email='userA@freesound.org', password='testpass')
        admin_change_url = reverse('admin:auth_user_change', args=[userA.id])

        post_data = {'username': u'userA',
                     'email': userA.email,  # Required to avoid breaking unique constraint with empty email
                     'date_joined_0': "2015-10-06", 'date_joined_1': "16:42:00"}  # date_joined required

        # Test save user without changing username
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)

        # Now rename user for the first time
        post_data.update({'username': u'userANewName'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        self.assertEqual(OldUsername.objects.filter(username='userA', user=userA).count(), 1)

        # Now rename user for the second time
        post_data.update({'username': u'userANewNewName'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        self.assertEqual(OldUsername.objects.filter(username='userANewName', user=userA).count(), 1)
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try rename user with an existing username from another user
        userB = User.objects.create_user('userB', email='userB@freesound.org')
        post_data.update({'username': userB.username})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(bool(resp.context['adminform'].errors), True)  # Error in username field
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try rename user with a username that was already used by the same user in the past
        post_data.update({'username': u'userA'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(bool(resp.context['adminform'].errors), True)  # Error in username field
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try to rename for a third time to a valid username. Because we are in admin now, the USERNAME_CHANGE_MAX_TIMES
        # restriction does not apply so rename should work correctly
        post_data.update({'username': u'userANewNewNewName'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        self.assertEqual(OldUsername.objects.filter(username='userANewNewName', user=userA).count(), 1)
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 3)


class UsernameValidatorTests(TestCase):
    """ Makes sure that username validation works as intended """
    class TestForm(forms.Form):
        username = UsernameField()

    def test_valid(self):
        """ Alphanumerics, _, - and + are ok"""
        form = self.TestForm(data={'username': 'normal_user.name+'})
        self.assertTrue(form.is_valid())

    def test_email_like_invalid(self):
        """ We don't allow @ character """
        form = self.TestForm(data={'username': 'email@username'})
        self.assertFalse(form.is_valid())

    def test_short_invalid(self):
        """ Should be longer than 3 characters """
        form = self.TestForm(data={'username': 'a'})
        self.assertFalse(form.is_valid())

    def test_long_invalid(self):
        """ Should be shorter than 30 characters """
        form = self.TestForm(data={'username': 'a'*31})
        self.assertFalse(form.is_valid())


class AboutFieldVisibilityTests(TestCase):
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


class EmailBounceTests(TestCase):

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
        pass  # TODO

    def test_request_email_change(self):
        pass  # TODO

    @override_settings(AWS_REGION='dummy_region')
    @override_settings(AWS_ACCESS_KEY_ID='dummy_id')
    @override_settings(AWS_SECRET_ACCESS_KEY='dummy_secret')
    @override_settings(AWS_SQS_QUEUE_URL='dummy_url')
    @mock.patch('accounts.management.commands.process_email_bounces.client')
    def test_populate_bounce(self, client):
        message_body = json.dumps({
            "Type": "Notification",
            "Message": json.dumps({
                "notificationType": "Bounce",
                "bounce": {
                    "bounceType": "Permanent",
                    "bounceSubType": "Suppressed",
                    "bouncedRecipients": [{"emailAddress": "user@freesound.org"}],
                    "timestamp": "2018-05-20T13:54:37.821Z"
                }
            })
        })

        client_obj = mock.MagicMock()
        client_obj.receive_message.return_value = {u'Messages': [{u'Body': message_body, u'ReceiptHandle': 'dummy'}]}
        client.return_value = client_obj

        def _delete_message(**kwargs):
            client_obj.receive_message.return_value = {u'Messages': []}
        client_obj.delete_message.side_effect = _delete_message

        user = User.objects.create_user('user', email='user@freesound.org')
        call_command('process_email_bounces')

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


class BulkDescribe(TestCase):

    fixtures = ['initial_data']

    @override_settings(CSV_PATH=tempfile.mkdtemp())
    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    @mock.patch('gearman.GearmanClient.submit_job')
    def test_upload_csv(self, submit_job):
        user = User.objects.create_user("testuser", password="testpass")
        self.client.login(username='testuser', password='testpass')

        # Test successful file upload and redirect
        filename = "file.csv"
        f = SimpleUploadedFile(filename, "file_content")
        resp = self.client.post(reverse('accounts-describe'), {u'bulk-csv_file': f})
        bulk = BulkUploadProgress.objects.get(user=user)
        self.assertRedirects(resp, reverse('accounts-bulk-describe', args=[bulk.id]))

        # Test really file exists
        self.assertEqual(os.path.exists(bulk.csv_path), True)

        # Test gearman job is triggered
        submit_job.assert_called_once_with("validate_bulk_describe_csv", str(bulk.id),
                                           wait_until_complete=False, background=True)

        # Delete tmp directory
        shutil.rmtree(settings.CSV_PATH)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_view_permissions(self):
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="N", user=user, original_csv_filename="test.csv")

        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        expected_redirect_url = reverse('accounts-login') + '?next=%s' % reverse('accounts-bulk-describe',
                                                                                 args=[bulk.id])
        self.assertRedirects(resp, expected_redirect_url)  # If user not logged in, redirect to login page

        self.client.login(username='testuser', password='testpass')
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertEqual(resp.status_code, 200)  # After login, page loads normally (200 OK)

        User.objects.create_user("testuser2", password="testpass", email='another_email@example.com')
        self.client.login(username='testuser2', password='testpass')
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertEqual(resp.status_code, 404)  # User without permission (not owner of object) gets 404

        with self.settings(BULK_UPLOAD_MIN_SOUNDS=10):
            # Now user is not allowed to load the page as user.profile.can_do_bulk_upload() returns False
            self.client.login(username='testuser', password='testpass')
            resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]), follow=True)
            self.assertRedirects(resp, reverse('accounts-home'))
            self.assertIn('Your user does not have permission to use the bulk describe', resp.content)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_validating(self):
        # Test that when BulkUploadProgress has not finished validation we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="N", user=user, original_csv_filename="test.csv")
        self.client.login(username='testuser', password='testpass')
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertIn('The uploaded data file has not yet been validated', resp.content)

    @mock.patch('gearman.GearmanClient.submit_job')
    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_finished_validation(self, submit_job):
        # Test that when BulkUploadProgress has finished validation we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="V", user=user, original_csv_filename="test.csv")
        self.client.login(username='testuser', password='testpass')
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertIn('Validation results of the data file', resp.content)

        # Test that chosing option to delete existing BulkUploadProgress really does it
        resp = self.client.post(reverse('accounts-bulk-describe', args=[bulk.id]) + '?action=delete')
        self.assertRedirects(resp, reverse('accounts-describe'))  # Redirects to describe page after delete
        self.assertEquals(BulkUploadProgress.objects.filter(user=user).count(), 0)

        # Test that chosing option to start describing files triggers bulk describe gearmnan job
        bulk = BulkUploadProgress.objects.create(progress_type="V", user=user, original_csv_filename="test.csv")
        resp = self.client.post(reverse('accounts-bulk-describe', args=[bulk.id]) + '?action=start')
        self.assertEqual(resp.status_code, 200)
        submit_job.assert_called_once_with("bulk_describe", str(bulk.id), wait_until_complete=False, background=True)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_description_in_progress(self):
        # Test that when BulkUploadProgress has started description and processing we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="S", user=user, original_csv_filename="test.csv")
        self.client.login(username='testuser', password='testpass')
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertIn('Your sounds are being described and processed', resp.content)

        # Test that when BulkUploadProgress has finished describing items but still is processing some sounds, we
        # show that info to the users. First we fake some data for the bulk object
        bulk.progress_type = 'F'
        bulk.validation_output = {
            'lines_ok': range(5),  # NOTE: we only use the length of these lists, so we fill them with irrelevant data
            'lines_with_errors': range(2),
            'global_errors': [],
        }
        bulk.description_output = {
            '1': 1,  # NOTE: we only use the length of the dict so we fill it with irrelevant values/keys
            '2': 2,
            '3': 3,
        }
        bulk.save()
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertIn('Your sounds are being described and processed', resp.content)

        # Test that when both description and processing have finished we show correct info to users
        for i in range(0, 5):  # First create the sound objects so BulkUploadProgress can properly compute progress
            Sound.objects.create(user=user,
                                 original_filename="Test sound %i" % i,
                                 license=License.objects.all()[0],
                                 md5="fakemd5%i" % i,
                                 moderation_state="OK",
                                 processing_state="OK")

        bulk.progress_type = 'F'
        bulk.description_output = {}
        for count, sound in enumerate(user.sounds.all()):
            bulk.description_output[count] = sound.id  # Fill bulk.description_output with real sound IDs
        bulk.save()
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertIn('The bulk description process has finished!', resp.content)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_closed(self):
        # Test that when BulkUploadProgress object is closed we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="C", user=user, original_csv_filename="test.csv")
        self.client.login(username='testuser', password='testpass')
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertIn('This bulk description process is closed', resp.content)


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
                                                email='reporter_{0}@example.com'.format(i))
            self.reporters.append(reporter)

        # Create user posting spam
        self.spammer = User.objects.create_user(username='spammer', email='spammer@example.com')

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
        # NOTE: we only test for the case of sound comments as the logic that handles this si common for all other
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
