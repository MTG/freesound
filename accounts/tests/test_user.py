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
import re
from unittest import skipIf, mock

from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from accounts.forms import FsPasswordResetForm, DeleteUserForm, UsernameField
from accounts.models import Profile, SameUser, ResetEmailRequest, OldUsername, DeletedUser, UserDeletionRequest
from comments.models import Comment
from forum.models import Thread, Post, Forum
from general.tasks import DELETE_USER_DELETE_SOUNDS_ACTION_NAME, DELETE_USER_KEEP_SOUNDS_ACTION_NAME
from sounds.models import License, Sound, Pack, DeletedSound, Download, PackDownload
from utils.mail import transform_unique_email
from utils.test_helpers import create_user_and_sounds


class UserRegistrationAndActivation(TestCase):
    fixtures = ['users']

    def test_user_save(self):
        u = User.objects.create_user("testuser2", password="testpass")
        self.assertEqual(Profile.objects.filter(user=u).exists(), True)
        u.save()  # Check saving user again (with existing profile) does not fail

    @mock.patch("django_recaptcha.fields.ReCaptchaField.validate")
    def test_user_registration(self, magic_mock_function):
        username = 'new_user'

        # Try registration without accepting tos
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': [username],
            'password1': ['123456!@'],
            'accepted_tos': [''],
            'email1': ['example@email.com'],
            'email2': ['example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'You must accept the terms of use')
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try registration with bad email
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': [username],
            'password1': ['12345678'],
            'accepted_tos': ['on'],
            'email1': ['example@email.com'],
            'email2': ['example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'This password is entirely numeric')
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try registration with bad password
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': [username],
            'password1': ['123456!@'],
            'accepted_tos': ['on'],
            'email1': ['exampleemail.com'],
            'email2': ['exampleemail.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Enter a valid email')
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try registration with no username
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': [''],
            'password1': ['123456!@'],
            'accepted_tos': ['on'],
            'email1': ['example@email.com'],
            'email2': ['example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'This field is required')
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try registration with different email addresses
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': [''],
            'password1': ['123456!@'],
            'accepted_tos': ['on'],
            'email1': ['example@email.com'],
            'email2': ['exampl@email.net']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Please confirm that your email address is the same')
        self.assertEqual(User.objects.filter(username=username).count(), 0)
        self.assertEqual(len(mail.outbox), 0)  # No email sent

        # Try successful registration
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': [username],
            'password1': ['123456!@'],
            'accepted_tos': ['on'],
            'email1': ['example@email.com'],
            'email2': ['example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'feedbackRegistration=1')
        self.assertEqual(User.objects.filter(username=username).count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # An email was sent!
        self.assertTrue(settings.EMAIL_SUBJECT_PREFIX in mail.outbox[0].subject)
        self.assertTrue(settings.EMAIL_SUBJECT_ACTIVATION_LINK in mail.outbox[0].subject)

        # Try register again with same username
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': [username],
            'password1': ['123456!@'],
            'accepted_tos': ['on'],
            'email1': ['example@email.com'],
            'email2': ['example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'You cannot use this username to create an account')
        self.assertEqual(User.objects.filter(username=username).count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # No new email sent

        # Try with repeated email address
        resp = self.client.post(reverse('accounts-registration-modal'), data={
            'username': ['a_different_username'],
            'password1': ['123456!@'],
            'accepted_tos': ['on'],
            'email1': ['example@email.com'],
            'email2': ['example@email.com']
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'You cannot use this email address to create an account')
        self.assertEqual(User.objects.filter(username=username).count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # No new email sent

        activation_code = re.search(r"home/activate/.+/(.+)/", mail.outbox[0].body).group(1)
        # Test calling accounts-activate with good hash, user should be activated
        resp = self.client.get(reverse('accounts-activate', args=[username, activation_code]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['all_ok'], True)
        self.assertEqual(User.objects.get(username=username).is_active, True)

    def test_user_activation_fails(self):
        user = User.objects.get(username="User6Inactive")  # Inactive user in fixture

        # Test calling accounts-activate with wrong hash, user should not be activated
        bad_hash = '4dad3dft'
        resp = self.client.get(reverse('accounts-activate', args=[user.username, bad_hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['decode_error'], True)
        self.assertEqual(User.objects.get(username="User6Inactive").is_active, False)

        # Test calling accounts-activate for a user that does not exist
        resp = self.client.get(reverse('accounts-activate', args=["noone", hash]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['user_does_not_exist'], True)


class UserDelete(TestCase):
    fixtures = ['licenses', 'sounds']

    def create_user_and_content(self, username="testuser", is_index_dirty=True):
        user = User.objects.create_user(username, password="testpass", email=f"{username}@freesound.org")
        OldUsername.objects.create(user=user, username=f"{username}_old_username")

        # Create comments
        target_sound = Sound.objects.all()[0]
        for i in range(0, 3):
            target_sound.add_comment(user, f"{username} comment {i}")
        # Create threads and posts 
        forum, _ = Forum.objects.get_or_create(name="Test forum")
        self.forum = forum
        thread = Thread.objects.create(author=user, title=f"Test thread by {username}", forum=forum)
        for i in range(0, 3):
            Post.objects.create(author=user, thread=thread, body="Post %i body" % i)
        # Create sounds and packs
        pack = Pack.objects.create(user=user, name=f"Test pack by {username}")
        for i in range(0, 3):
            Sound.objects.create(user=user,
                                 original_filename=f"Test sound {i} by {username}",
                                 pack=pack,
                                 is_index_dirty=is_index_dirty,
                                 license=License.objects.all()[0],
                                 md5=f"fake_unique_md5_{i}_{username}",
                                 moderation_state="OK",
                                 processing_state="OK")
        return user

    def test_user_delete_make_invalid_password(self):
        user = self.create_user_and_content(is_index_dirty=False)
        user.profile.delete_user()
        self.assertFalse(user.has_usable_password())

    def test_user_delete_keep_sounds(self):
        # This should set user's attribute active to false and anonymize it
        # Sounds and other user content should not be deleted
        user = self.create_user_and_content(is_index_dirty=False)
        user.profile.delete_user()
        self.assertEqual(User.objects.get(id=user.id).profile.is_anonymized_user, True)

        self.assertEqual(user.username, f"deleted_user_{user.id}")
        self.assertEqual(user.profile.about, '')
        self.assertEqual(user.profile.home_page, '')
        self.assertEqual(user.profile.signature, '')
        self.assertEqual(user.profile.geotag, None)
        self.assertTrue(DeletedUser.objects.filter(user_id=user.id).exists())
        self.assertFalse(OldUsername.objects.filter(user__id=user.id).exists())

        self.assertTrue(Comment.objects.filter(user__id=user.id).exists())
        self.assertTrue(Thread.objects.filter(author__id=user.id).exists())
        self.assertTrue(Post.objects.filter(author__id=user.id).exists())
        self.assertFalse(DeletedSound.objects.filter(user__id=user.id).exists())
        self.assertTrue(Pack.objects.filter(user__id=user.id).exists())
        self.assertTrue(Sound.objects.filter(user__id=user.id).exists())
        self.assertTrue(Sound.objects.filter(user__id=user.id)[0].is_index_dirty)

    @mock.patch('sounds.models.delete_sound_from_gaia')
    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_user_delete_include_sounds(self, delete_sounds_from_search_engine, delete_sound_from_gaia):
        # This should set user's attribute deleted_user to True and anonymize it
        # Sounds and Packs should be deleted (creating DeletedSound objects), but other user content should be preserved
        user = self.create_user_and_content()
        user_sounds = Sound.objects.filter(user=user)
        user_sound_ids = [s.id for s in user_sounds]
        user.profile.delete_user(remove_sounds=True)

        self.assertEqual(User.objects.get(id=user.id).profile.is_anonymized_user, True)
        self.assertEqual(user.username, f"deleted_user_{user.id}")
        self.assertEqual(user.profile.about, '')
        self.assertEqual(user.profile.home_page, '')
        self.assertEqual(user.profile.signature, '')
        self.assertEqual(user.profile.geotag, None)
        self.assertTrue(DeletedUser.objects.filter(user_id=user.id).exists())
        self.assertFalse(OldUsername.objects.filter(user__id=user.id).exists())

        self.assertTrue(Comment.objects.filter(user__id=user.id).exists())
        self.assertTrue(Thread.objects.filter(author__id=user.id).exists())
        self.assertTrue(Post.objects.filter(author__id=user.id).exists())
        self.assertTrue(Pack.objects.filter(user__id=user.id).exists())
        self.assertTrue(Pack.objects.filter(user__id=user.id).all()[0].is_deleted)
        self.assertFalse(Sound.objects.filter(user__id=user.id).exists())
        self.assertTrue(DeletedSound.objects.filter(user__id=user.id).exists())

        delete_sounds_from_search_engine.assert_has_calls([mock.call([i]) for i in user_sound_ids], any_order=True)
        delete_sound_from_gaia.assert_has_calls([mock.call(i) for i in user_sound_ids], any_order=True)

    @mock.patch('sounds.models.delete_sound_from_gaia')
    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_user_delete_sounds_and_user_object(self, delete_sounds_from_search_engine, delete_sound_from_gaia):
        # This should delete all user content, including the User object, and create a DeletedUser object. This will
        # create DeletedSound objects.
        user = self.create_user_and_content()
        user_sounds = Sound.objects.filter(user=user)
        user_sound_ids = [s.id for s in user_sounds]
        user.profile.delete_user(remove_sounds=True, delete_user_object_from_db=True)

        self.assertFalse(User.objects.filter(id=user.id).exists())
        self.assertTrue(DeletedUser.objects.filter(user_id=user.id).exists())
        self.assertFalse(Comment.objects.filter(user__id=user.id).exists())
        self.assertFalse(Thread.objects.filter(author__id=user.id).exists())
        self.assertFalse(Post.objects.filter(author__id=user.id).exists())
        self.assertFalse(Pack.objects.filter(user__id=user.id).exists())
        self.assertFalse(Sound.objects.filter(user__id=user.id).exists())
        self.assertTrue(DeletedSound.objects.filter(user__id=user.id).exists())
        self.assertFalse(OldUsername.objects.filter(user__id=user.id).exists())

        delete_sounds_from_search_engine.assert_has_calls([mock.call([i]) for i in user_sound_ids], any_order=True)
        delete_sound_from_gaia.assert_has_calls([mock.call(i) for i in user_sound_ids], any_order=True)

    @skipIf(True, "This tests a method that should never be called")
    @mock.patch('sounds.models.delete_sound_from_gaia')
    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_user_full_delete(self, delete_sounds_from_search_engine, delete_sound_from_gaia):
        # This should delete all user content, including the User object and without creating DeletedUser. It does
        # create however DeletedSound objects.
        user = self.create_user_and_content()
        user_sounds = Sound.objects.filter(user=user)
        user_sound_ids = [s.id for s in user_sounds]
        # NOTE: this test is skipped because user.delete() should never be directly called but the
        # user.profile.delete_sound(...) method should be called instead. If user.delete() is to be called
        # directly, Sound.objects.filter(user=user).delete() should be called before to avoid issues related
        # to the order in which objects are deleted.
        user.delete()

        self.assertFalse(User.objects.filter(id=user.id).exists())
        self.assertFalse(OldUsername.objects.filter(user__id=user.id).exists())
        self.assertFalse(DeletedUser.objects.filter(user_id=user.id).exists())
        self.assertFalse(Comment.objects.filter(user__id=user.id).exists())
        self.assertFalse(Thread.objects.filter(author__id=user.id).exists())
        self.assertFalse(Post.objects.filter(author__id=user.id).exists())
        self.assertFalse(Pack.objects.filter(user__id=user.id).exists())
        self.assertFalse(Sound.objects.filter(user__id=user.id).exists())
        self.assertTrue(DeletedSound.objects.filter(user__id=user.id).exists())

        calls = [mock.call(i) for i in user_sound_ids]
        delete_sounds_from_search_engine.assert_has_calls(calls, any_order=True)
        delete_sound_from_gaia.assert_has_calls(calls, any_order=True)


    @mock.patch('general.tasks.delete_user.delay')
    def test_user_delete_include_sounds_using_web_form(self, submit_job):
        # Test user's option to delete user account including the sounds

        user = self.create_user_and_content(is_index_dirty=False)
        self.client.force_login(user)
        form = DeleteUserForm(user_id=user.id)
        encr_link = form.initial['encrypted_link']
        resp = self.client.post(
            reverse('accounts-delete'),
            {'encrypted_link': encr_link, 'password': 'testpass', 'delete_sounds': 'delete_sounds'},
            follow=True,
        )

        # Test job is triggered
        data = json.dumps({'user_id': user.id, 'action': DELETE_USER_DELETE_SOUNDS_ACTION_NAME,
                    'deletion_reason': DeletedUser.DELETION_REASON_SELF_DELETED})
        submit_job.assert_called_once_with(user_id=user.id, deletion_action=DELETE_USER_DELETE_SOUNDS_ACTION_NAME, deletion_reason=DeletedUser.DELETION_REASON_SELF_DELETED)

        # Test UserDeletionRequest object is created with status "tr" (Deletion action was triggered)
        self.assertTrue(UserDeletionRequest.objects.filter(
            user_from=user, user_to=user,
            status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED).exists())

        # Assert user is redirected to front page
        self.assertRedirects(resp, reverse('front-page'))

        # Check loaded page contains message about user deletion
        self.assertContains(resp, 'Your user account will be deleted in a few moments')

    @mock.patch('general.tasks.delete_user.delay')
    def test_user_delete_keep_sounds_using_web_form(self, submit_job):
        # Test user's option to delete user account but preserving the sounds

        user = self.create_user_and_content(is_index_dirty=False)
        self.client.force_login(user)
        form = DeleteUserForm(user_id=user.id)
        encr_link = form.initial['encrypted_link']
        resp = self.client.post(
            reverse('accounts-delete'),
            {'encrypted_link': encr_link, 'password': 'testpass', 'delete_sounds': 'only_user'},
            follow=True,
        )

        # Test job is triggered
        data = json.dumps({'user_id': user.id, 'action': DELETE_USER_KEEP_SOUNDS_ACTION_NAME,
                           'deletion_reason': DeletedUser.DELETION_REASON_SELF_DELETED})
        submit_job.assert_called_once_with(user_id=user.id, deletion_action=DELETE_USER_KEEP_SOUNDS_ACTION_NAME, deletion_reason=DeletedUser.DELETION_REASON_SELF_DELETED)
        
        # Test UserDeletionRequest object is created with status "tr" (Deletion action was triggered)
        self.assertTrue(UserDeletionRequest.objects.filter(
            user_from=user, user_to=user,
            status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED).exists())

        # Assert user is redirected to front page
        self.assertRedirects(resp, reverse('front-page'))

        # Check loaded page contains message about user deletion
        self.assertContains(resp, 'Your user account will be deleted in a few moments')

    def test_fail_user_delete_include_sounds_using_web_form(self):
        # Test delete user account form with wrong password does not delete

        # This should try to delete the account but with a wrong password
        user = self.create_user_and_content(is_index_dirty=False)
        self.client.force_login(user)
        form = DeleteUserForm(user_id=user.id)
        encr_link = form.initial['encrypted_link']
        resp = self.client.post(
            reverse('accounts-delete'),
            {'encrypted_link': encr_link, 'password': 'wrong_pass', 'delete_sounds': 'delete_sounds'})

        # Check user is reported incorrect password
        self.assertContains(resp, 'Incorrect password')

        # Check user is not marked as anonymized
        self.assertEqual(User.objects.get(id=user.id).profile.is_anonymized_user, False)

        # Check sounds still exist
        self.assertTrue(Sound.objects.filter(user__id=user.id).exists())

        # Check no DeletedUser object has been created for that user
        self.assertFalse(DeletedUser.objects.filter(user_id=user.id).exists())

    def test_delete_user_reasons(self):
        # Tests that the reasons passed to Profile.delete_user() are effectively added to the created DeletedUser object
        for reason in [DeletedUser.DELETION_REASON_SELF_DELETED,
                       DeletedUser.DELETION_REASON_DELETED_BY_ADMIN,
                       DeletedUser.DELETION_REASON_SPAMMER]:
            user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
            user.profile.delete_user(deletion_reason=reason)
            self.assertEqual(DeletedUser.objects.get(user_id=user.id).reason, reason)

    @mock.patch('sounds.models.delete_sound_from_gaia')
    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    @mock.patch('forum.models.delete_posts_from_search_engine')
    def test_delete_user_with_count_fields_out_of_sync(self, delete_posts_from_search_engine, delete_sounds_from_search_engine,
                                                       delete_sound_from_gaia):
        # Test that deleting a user work properly even when the profile count fields (num_sounds, num_posts,
        # num_sound_downloads and num_pack_downloads) are out of sync. This is a potential issue because if the
        # count fields are not right, deleting sound/download/post objects related to that user might trigger
        # signals that would set the count field to values < 0 and would break the DB constraint imposed by these
        # count fields being of type PositiveIntegerField. Here we test that the user delete method can handle
        # these cases without raising errors.

        # Create user, associated content and download objects
        user = self.create_user_and_content()
        for sound in Sound.objects.filter(user=user):
            Download.objects.create(user=user, sound=sound, license_id=sound.license_id)
        for pack in Pack.objects.filter(user=user):
            PackDownload.objects.create(user=user, pack=pack)
        user.profile.refresh_from_db()
        user.profile.update_num_sounds()

        # Make sure the count fields are in sync
        self.assertEqual(user.profile.num_sound_downloads, Sound.objects.filter(user=user).count())
        self.assertEqual(user.profile.num_pack_downloads, Pack.objects.filter(user=user).count())
        self.assertEqual(user.profile.num_sounds, Sound.objects.filter(user=user).count())
        self.assertEqual(user.profile.num_posts, Post.objects.filter(author=user).count())

        # Decrease by one all count fields (make them be out of sync)
        user.profile.num_sound_downloads = user.profile.num_sound_downloads - 1
        user.profile.num_pack_downloads = user.profile.num_pack_downloads - 1
        user.profile.num_sounds = user.profile.num_sounds - 1
        user.profile.num_posts = user.profile.num_posts - 1
        user.profile.save()

        # Also set count fields of objects related to those that will be deleted to be out-of-sync
        self.forum.num_threads = 0
        self.forum.save()

        # Delete user including sounds (which will delete Download objects as well) and also deleting the User object
        # from DB which will trigger deleting associated content like posts, etc.
        # That should not fail even if the count fields are out of sync
        user.profile.refresh_from_db()
        user.profile.delete_user(remove_sounds=True, delete_user_object_from_db=True)

    @override_settings(CHECK_ASYNC_DELETED_USERS_HOURS_BACK=0)
    @mock.patch('general.tasks.delete_user.delay')
    def test_check_async_deleted_users_command(self, submit_job):

        def delete_user_using_web_view(user):
            self.client.force_login(user)
            form = DeleteUserForm(user_id=user.id)
            encr_link = form.initial['encrypted_link']
            resp = self.client.post(
                reverse('accounts-delete'),
                {'encrypted_link': encr_link, 'password': 'testpass', 'delete_sounds': 'only_user'})
            self.assertRedirects(resp, reverse('front-page'))

        def call_command_get_console_log_output(command):
            with self.assertLogs('console', 'INFO') as cm:
                call_command(command)
                return "\n".join(cm.output)

        # Create 3 users for the tests below
        user1 = self.create_user_and_content(username="testuser1")
        user2 = self.create_user_and_content(username="testuser2")

        # Run command, it should say that there are 0 users that should have been deleted
        cmd_output = call_command_get_console_log_output("check_async_deleted_users")
        self.assertEqual(UserDeletionRequest.objects.all().count(), 0)
        self.assertIn('Found 0 users that should have been deleted and were not', cmd_output)

        # Now delete user1 using the web form to trigger async download. submit_job function is mocked so the user
        # will not be deleted in practice, but UserDeletionRequest object should have been created
        delete_user_using_web_view(user1)
        #  Check a UserDeletionRequest was created...
        self.assertEqual(UserDeletionRequest.objects.all().count(), 1)
        # ...but check also that user was not really deleted
        user1.refresh_from_db()
        self.assertEqual(user1.profile.is_anonymized_user, False)

        # Run the command again, it should say that there is 1 user that should have been deleted
        cmd_output = call_command_get_console_log_output("check_async_deleted_users")
        self.assertIn('Found 1 users that should have been deleted and were not', cmd_output)

        # Now delete user2 using the web form to trigger async download. submit_job function is mocked so the user
        # will not be deleted in practice, but UserDeletionRequest object should have been created
        delete_user_using_web_view(user2)
        # Check a UserDeletionRequest was created
        self.assertEqual(UserDeletionRequest.objects.all().count(), 2)

        # Run the command again, it should say that there are 2 users that should have been deleted
        cmd_output = call_command_get_console_log_output("check_async_deleted_users")
        self.assertIn('Found 2 users that should have been deleted and were not', cmd_output)

        # Do the actual deletion of the user as if the async task was triggered
        # Check that user was deleted and UserDeletionRequest status was also updated
        user2.profile.delete_user()
        user2.refresh_from_db()
        self.assertEqual(user2.profile.is_anonymized_user, True)
        self.assertEqual(UserDeletionRequest.objects.get(user_to=user2).status,
                         UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED)

        # Run the command again, it should say that there is 1 user that should have been deleted
        cmd_output = call_command_get_console_log_output("check_async_deleted_users")
        self.assertIn('Found 1 users that should have been deleted and were not', cmd_output)

        # Now for user1, mark it as having been anonymized but without updating UserDeletionRequest status
        user1.profile.is_anonymized_user = True
        user1.profile.save()

        # Run the command again, it should say that there are 0 user that should have been deleted, and it should
        # have updated the UserDeletionRequest status for user 1
        cmd_output = call_command_get_console_log_output("check_async_deleted_users")
        self.assertIn('Found 0 users that should have been deleted and were not', cmd_output)
        self.assertEqual(UserDeletionRequest.objects.get(user_to=user1).status,
                         UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED)


class UserDeletionRequestTestCase(TestCase):

    def test_deleting_user_updates_existing_deletion_request_objects(self):
        # Tests that when a user is deleted which had existing UserDeletionRequest objects assigned, these objects
        # get the status updated and the DeletedUser object is added to them
        username = "testuser"

        # Test when deleting a user but preserving the user object in DB (anonymizing)
        user = User.objects.create_user(username, password="testpass", email='email@freesound.org')
        UserDeletionRequest.objects.create(user_to=user, username_to=username)
        user.profile.delete_user()
        deletion_request = UserDeletionRequest.objects.get(username_to=username)
        deleted_user = DeletedUser.objects.get(username=username)
        self.assertEqual(deletion_request.status, UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED)
        self.assertEqual(deletion_request.deleted_user_id, deleted_user.id)
        deletion_request.delete()
        deleted_user.delete()

        # Test when deleting a user and also deleting the user object in DB
        user = User.objects.create_user(username, password="testpass", email='email@freesound.org')
        UserDeletionRequest.objects.create(user_to=user, username_to=username)
        user.profile.delete_user(delete_user_object_from_db=True)
        deletion_request = UserDeletionRequest.objects.get(username_to=username)
        deleted_user = DeletedUser.objects.get(username=username)
        self.assertEqual(deletion_request.status, UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED)
        self.assertEqual(deletion_request.deleted_user_id, deleted_user.id)
        deletion_request.delete()
        deleted_user.delete()

        # Test with multiple requests
        user = User.objects.create_user(username, password="testpass", email='email@freesound.org')
        UserDeletionRequest.objects.create(user_to=user, username_to=username)
        UserDeletionRequest.objects.create(user_to=user, username_to=username)
        user.profile.delete_user()
        deleted_user = DeletedUser.objects.get(username=username)
        for deletion_request in UserDeletionRequest.objects.filter(username_to=username):
            self.assertEqual(deletion_request.status, UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED)
            self.assertEqual(deletion_request.deleted_user_id, deleted_user.id)

    def test_user_deletion_request_update_status_history(self):
        # Test that when updating a UserDeletionRequest object and changing the status, the change gets recorded
        # in the status_history field
        username = "testusername"
        user = User.objects.create_user(username, password="testpass", email='email@freesound.org')
        deletion_request = UserDeletionRequest.objects.create(user_to=user, username_to=username, status="re")
        self.assertEqual(deletion_request.status, UserDeletionRequest.DELETION_REQUEST_STATUS_RECEIVED_REQUEST)
        self.assertEqual(len(deletion_request.status_history), 1)
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_RECEIVED_REQUEST in
                        deletion_request.status_history[0])

        # Change status: status history should be updated
        deletion_request.status = UserDeletionRequest.DELETION_REQUEST_STATUS_WAITING_FOR_USER
        deletion_request.save()
        self.assertEqual(deletion_request.status, UserDeletionRequest.DELETION_REQUEST_STATUS_WAITING_FOR_USER)
        self.assertEqual(len(deletion_request.status_history), 2)
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_RECEIVED_REQUEST in
                        deletion_request.status_history[0])
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_WAITING_FOR_USER in
                        deletion_request.status_history[1])

        # Now save again, but don't change status: status history should not be updated
        deletion_request.save()
        self.assertEqual(deletion_request.status, UserDeletionRequest.DELETION_REQUEST_STATUS_WAITING_FOR_USER)
        self.assertEqual(len(deletion_request.status_history), 2)
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_RECEIVED_REQUEST in
                        deletion_request.status_history[0])
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_WAITING_FOR_USER in
                        deletion_request.status_history[1])

        # Now change status again: status history should be updated
        deletion_request.status = UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED
        deletion_request.save()
        self.assertEqual(deletion_request.status, UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED)
        self.assertEqual(len(deletion_request.status_history), 3)
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_RECEIVED_REQUEST in
                        deletion_request.status_history[0])
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_WAITING_FOR_USER in
                        deletion_request.status_history[1])
        self.assertTrue(UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED in
                        deletion_request.status_history[2])


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

        self.client.logout()
        # Now try with user_b and user_c. User b had a shared email with user_c. Even if user_b's email was
        # not changed, he is still redirected to the duplicate email cleanup page
        resp = self.client.post(reverse('login'),
                                {'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('accounts-multi-email-cleanup') + f"?next={reverse('messages')}")
        self.client.logout()
        resp = self.client.post(reverse('login'),
                                {'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('accounts-multi-email-cleanup') + f"?next={reverse('messages')}")

    def test_fix_email_issues_with_secondary_user_email_change(self):
        # user_c changes his email and tries to login, redirect should go to email cleanup page and from there
        # directly to messages (2 redirect steps)
        self.user_c.email = 'new@email.com'  # Must be different than transform_unique_email('c@d.com')
        self.user_c.save()
        resp = self.client.post(reverse('login'), follow=True,
                                data={'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertEqual(resp.redirect_chain[0][0],
                          reverse('accounts-multi-email-cleanup') + f"?next={reverse('messages')}")
        self.assertEqual(resp.redirect_chain[1][0], reverse('messages'))

        # Also check that related SameUser objects have been removed
        self.assertEqual(SameUser.objects.all().count(), 0)

        self.client.logout()
        # Now next time user_c tries to go to messages again, there is only one redirect (like for user_a)
        resp = self.client.post(reverse('login'),
                                {'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

        self.client.logout()
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
        self.assertEqual(resp.redirect_chain[0][0],
                          reverse('accounts-multi-email-cleanup') + f"?next={reverse('messages')}")
        self.assertEqual(resp.redirect_chain[1][0], reverse('messages'))

        # Check that user_c email was changed
        self.user_c = User.objects.get(id=self.user_c.id)  # Reload user from db
        self.assertEqual(self.user_c.email, self.original_shared_email)

        # Also check that related SameUser objects have been removed
        self.assertEqual(SameUser.objects.all().count(), 0)

        self.client.logout()
        # Now next time user_b tries to go to messages again, there is only one redirect (like for user_a)
        resp = self.client.post(reverse('login'),
                                {'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

        self.client.logout()
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
        self.assertEqual(resp.redirect_chain[0][0],
                          reverse('accounts-multi-email-cleanup') + f"?next={reverse('messages')}")
        self.assertEqual(resp.redirect_chain[1][0], reverse('messages'))

        # Check that user_c email was not changed
        self.user_c = User.objects.get(id=self.user_c.id)  # Reload user from db
        self.assertEqual(self.user_c.email, 'new2w@email.com')

        # Also check that related SameUser objects have been removed
        self.assertEqual(SameUser.objects.all().count(), 0)

        self.client.logout()
        # Now next time user_b tries to go to messages again, there is only one redirect (like for user_a)
        resp = self.client.post(reverse('login'),
                                {'username': self.user_b, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

        self.client.logout()
        # Also if user_c logs in, redirect goes straight to messages
        resp = self.client.post(reverse('login'),
                                {'username': self.user_c, 'password': '12345', 'next': reverse('messages')})
        self.assertRedirects(resp, reverse('messages'))

    def test_user_profile_get_email(self):
        # Here we test that when we send an email to users that have SameUser objects we chose the right email address

        # user_a has no SameUser objects, emails should be sent directly to his address
        self.assertEqual(self.user_a.profile.get_email_for_delivery(), self.user_a.email)

        # user_b has SameUser with user_c, but user_b is main user so emails should be sent directly to his address
        self.assertEqual(self.user_b.profile.get_email_for_delivery(), self.user_b.email)

        # user_c should get emails at user_b email address (user_b is main user)
        self.assertEqual(self.user_c.profile.get_email_for_delivery(), self.user_b.email)

        # If we remove SameUser entries, email of user_c is sent directly to his address
        SameUser.objects.all().delete()
        self.assertEqual(self.user_c.profile.get_email_for_delivery(), self.user_c.email)


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
        self.client.post(reverse("problems-logging-in"), {"username_or_email": "testuser@freesound.org"})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[freesound] Password reset")

    @override_settings(SITE_ID=2)
    def test_reset_view_with_username(self):
        """Check that the reset password view calls our form"""
        Site.objects.create(id=2, domain="freesound.org", name="Freesound")
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        self.client.post(reverse("problems-logging-in"), {"username_or_email": "testuser"})

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[freesound] Password reset")


class EmailResetTestCase(TestCase):
    def test_reset_email_form(self):
        """ Check that reset email with the right parameters """
        user = User.objects.create_user("testuser", email="testuser@freesound.org")
        user.set_password('12345')
        user.save()
        self.client.force_login(user)
        resp = self.client.post(reverse('accounts-email-reset'), {
            'email': 'new_email@freesound.org',
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
        self.client.force_login(user)
        resp = self.client.post(reverse('accounts-email-reset'), {
            'email': 'new_email@freesound.org',
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
        self.client.force_login(user)
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
        resp = self.client.post(reverse('problems-logging-in'), {
            'username_or_email': 'testuser@freesound.org',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check email was sent
        self.assertTrue(settings.EMAIL_SUBJECT_PREFIX in mail.outbox[0].subject)
        self.assertTrue(settings.EMAIL_SUBJECT_ACTIVATION_LINK in mail.outbox[0].subject)

        resp = self.client.post(reverse('problems-logging-in'), {
            'username_or_email': 'new_email@freesound.org',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check no new email was sent (len() is same as before)

    def test_resend_activation_code_from_username(self):
        """
        Check that resend activation code doesn't return an error with post request (use username to identify user)
        """
        user = User.objects.create_user("testuser", email="testuser@freesound.org", is_active=False)
        resp = self.client.post(reverse('problems-logging-in'), {
            'username_or_email': 'testuser',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check email was sent
        self.assertTrue(settings.EMAIL_SUBJECT_PREFIX in mail.outbox[0].subject)
        self.assertTrue(settings.EMAIL_SUBJECT_ACTIVATION_LINK in mail.outbox[0].subject)

        resp = self.client.post(reverse('problems-logging-in'), {
            'username_or_email': 'testuser_does_not_exist',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)  # Check no new email was sent (len() is same as before)


class ChangeUsernameTest(TestCase):

    fixtures = ['licenses']

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
        userA = User.objects.create_user('userA', email='userA@freesound.org')
        self.client.force_login(userA)

        # Test save profile without changing username (note we set all mandatory fields)
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userA'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)

        # Try rename user with an existing username from another user
        userB = User.objects.create_user('userB', email='userB@freesound.org')
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': [userB.username], 'profile-ui_theme_preference': 'f'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['profile_form'].has_error('username'), True)  # Error in username field
        self.assertIn('This username is already taken or has been in used in the past',
                      str(resp.context['profile_form']['username'].errors))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userA')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)

        # Now rename user for the first time
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userANewName'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewName')
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 1)

        # Try rename again user with a username that was already used by the same user in the past
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userA'], 'profile-ui_theme_preference': 'f'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['profile_form'].has_error('username'), True)  # Error in username field
        self.assertIn('This username is already taken or has been in used in the past',
                      str(resp.context['profile_form']['username'].errors))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 1)

        # Now rename user for the second time
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userANewNewName'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try to rename for a third time to a valid username but it won't rename anymore because exceeded maximum
        # USERNAME_CHANGE_MAX_TIMES (which is set to 2 for this test)
        # NOTE: when USERNAME_CHANGE_MAX_TIMES is reached, the form renders the "username" field as "disabled" and
        # therefore the username can't be changed. Other than that the form behaves normally, therefore no
        # form errors will be raised because the field is ignored
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userANewNewNewName'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))  # Successful edit redirects to home but...
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # ...username has not changed...
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)  # ...and no new OldUsername objects created

    def test_change_username_mark_sounds_dirty(self):
        # Thest that changing username of a user that has sounds marks her sounds as dirty
        user, _, _ = create_user_and_sounds(num_sounds=3, num_packs=0)
        Sound.objects.filter(user=user).update(is_index_dirty=False)
        self.client.force_login(user)
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userANewNewName'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))
        user.refresh_from_db()
        self.assertEqual(user.username, 'userANewNewName')
        self.assertEqual(OldUsername.objects.filter(user=user).count(), 1)
        ss = Sound.objects.filter(user=user, is_index_dirty=True)
        self.assertEqual(ss.count(), 3)

    @override_settings(USERNAME_CHANGE_MAX_TIMES=2)
    def test_change_username_form_admin(self):
        superuser = User.objects.create_user('superuser', is_superuser=True, is_staff=True)
        self.client.force_login(superuser)

        # Create user and get admin change url
        userA = User.objects.create_user('userA', email='userA@freesound.org')
        admin_change_url = reverse('admin:auth_user_change', args=[userA.id])

        post_data = {'username': 'userA',
                     'email': userA.email,  # Required to avoid breaking unique constraint with empty email
                     'date_joined_0': "2015-10-06", 'date_joined_1': "16:42:00"}  # date_joined required

        # Test save user without changing username
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)

        # Now rename user for the first time
        post_data.update({'username': 'userANewName'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        self.assertEqual(OldUsername.objects.filter(username='userA', user=userA).count(), 1)

        # Now rename user for the second time
        post_data.update({'username': 'userANewNewName'})
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
        self.assertIn('This username is already taken or has been in used in the past',
                      str(resp.context['adminform'].errors))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try rename user with a username that was already used by the same user in the past
        post_data.update({'username': 'userA'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(bool(resp.context['adminform'].errors), True)  # Error in username field
        self.assertIn('This username is already taken or has been in used in the past',
                      str(resp.context['adminform'].errors))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try rename user with a username that was already used by the same user in the past, but using different
        # case for some characters
        post_data.update({'username': 'uSeRA'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(bool(resp.context['adminform'].errors), True)  # Error in username field
        self.assertIn('This username is already taken or has been in used in the past',
                      str(resp.context['adminform'].errors))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewNewName')  # Username has not changed
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 2)

        # Try to rename for a third time to a valid username. Because we are in admin now, the USERNAME_CHANGE_MAX_TIMES
        # restriction does not apply so rename should work correctly
        post_data.update({'username': 'userANewNewNewName'})
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        self.assertEqual(OldUsername.objects.filter(username='userANewNewName', user=userA).count(), 1)
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 3)

    def test_change_username_case_insensitiveness(self):
        """Test that changing the username for a new version of the username with different capitalization does not
        create a new OldUsername object. The username change is valid (e.g. userA > UserA), but it should not create
        OldUsername entry because usernames should be treated as case insensitive.
        """
        # Create user and login
        userA = User.objects.create_user('userA', email='userA@freesound.org')
        self.client.force_login(userA)

        # Rename "userA" to "UserA", should not create OldUsername object
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['UserA'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'UserA')  # Username capitalization was changed ...
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)  # ... but not OldUsername was created

    def test_oldusername_username_unique_case_insensitiveness(self):
        """Test that OldUsername.username is case insensitive at the DB level, and that we can't create objects
        with different "capitalizations" of username property"""
        userA = User.objects.create_user('userA', email='userA@freesound.org', password='testpass')
        OldUsername.objects.create(user=userA, username='newUserAUsername')
        with self.assertRaises(IntegrityError):
            OldUsername.objects.create(user=userA, username='NewUserAUsername')
    
    def test_username_whitespace(self):
        """Test that for usernames created before stronger validation was applied, whitespaces are a valid character
        but for new edited ones they are not."""
        userA = User.objects.create_user('user A', email='userA@freesound.org', password='testpass')
        self.client.force_login(userA)

        # Test save profile without changing username with whitespaces
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['user A'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 0)

        # Test save profile changing username (no whitespaces)
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userANewName'], 'profile-ui_theme_preference': 'f'})
        self.assertRedirects(resp, reverse('accounts-edit'))
        userA.refresh_from_db()
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 1)

        # Test save profile changing username (whitespaces -> fail)
        resp = self.client.post(reverse('accounts-edit'), data={'profile-username': ['userA SpaceName'], 'profile-ui_theme_preference': 'f'})
        self.assertEqual(resp.status_code, 200)
        userA.refresh_from_db()
        self.assertEqual(userA.username, 'userANewName')
        self.assertEqual(OldUsername.objects.filter(user=userA).count(), 1)

class ChangeEmailViaAdminTestCase(TestCase):

    def test_change_email_form_admin(self):
        superuser = User.objects.create_user('superuser', is_superuser=True, is_staff=True)
        self.client.force_login(superuser)

        # Create user and get admin change url
        userA = User.objects.create_user('userA', email='userA@freesound.org', password='testpass')
        admin_change_url = reverse('admin:auth_user_change', args=[userA.id])


        # Try to change email to some other (unused email)
        new_email = 'aNewEmail@freesound.org'
        post_data = {'username': userA.username,
                     'email': new_email,
                     'date_joined_0': "2015-10-06", 'date_joined_1': "16:42:00"}  # date_joined required
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertRedirects(resp, reverse('admin:auth_user_changelist'))  # Successful edit redirects to users list
        userA.refresh_from_db()
        self.assertEqual(userA.email, new_email)

        # Now create another user with a different email, and try to change userA email to the email of the new user
        userB = User.objects.create_user('userB', email='userBA@freesound.org', password='testpass')
        post_data = {'username': userA.username,
                     'email': userB.email,
                     'date_joined_0': "2015-10-06", 'date_joined_1': "16:42:00"}  # date_joined required
        resp = self.client.post(admin_change_url, data=post_data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(bool(resp.context['adminform'].errors), True)  # Error in email field
        self.assertIn('This email is already being used by another user', str(resp.context['adminform'].errors))
        userA.refresh_from_db()
        self.assertEqual(userA.email, new_email)  # Email has not been changed


class UsernameValidatorTest(TestCase):
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
        form = self.TestForm(data={'username': 'a' * 31})
        self.assertFalse(form.is_valid())
