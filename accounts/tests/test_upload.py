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
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings, skipIf
from django.urls import reverse

from sounds.models import License, Sound, Pack, BulkUploadProgress
from tags.models import Tag
from utils.filesystem import File
from utils.test_helpers import create_test_files, override_uploads_path_with_temp_directory, \
    override_csv_path_with_temp_directory, create_user_and_sounds, test_using_bw_ui


class UserUploadAndDescribeSounds(TestCase):
    fixtures = ['licenses', 'user_groups', 'moderation_queues', 'email_preference_type']

    @skipIf(True, "Test not ready for new uploader")
    @override_uploads_path_with_temp_directory
    def test_handle_uploaded_file_html(self):
        # TODO: test html5 file uploads when we change uploader
        user = User.objects.create_user("testuser", password="testpass")
        self.client.force_login(user)

        # Test successful file upload
        filename = "file.wav"
        f = SimpleUploadedFile(filename, b"file_content")
        resp = self.client.post("/home/upload/html/", {'file': f})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os.path.exists(settings.UPLOADS_PATH + '/%i/%s' % (user.id, filename)), True)

        # Test file upload that should fail
        filename = "filè.xyz"
        f = SimpleUploadedFile(filename, b"file_content")
        resp = self.client.post("/home/upload/html/", {'file': f})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(os.path.exists(settings.UPLOADS_PATH + '/%i/%s' % (user.id, filename)), False)

    @override_uploads_path_with_temp_directory
    def test_select_uploaded_files_to_describe(self):
        # Create audio files
        filenames = ['file1.wav', 'file2.wav', 'file3.wav', 'filè4.wav']
        user = User.objects.create_user("testuser", password="testpass")
        self.client.force_login(user)
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(filenames, user_upload_path)

        # Check that files are displayed in the template
        resp = self.client.get('/home/describe/')
        self.assertEqual(resp.status_code, 200)
        self.assertListEqual(sorted([os.path.basename(f.full_path) for f in resp.context['file_structure'].children]), sorted(filenames))

        # Selecting one file redirects to /home/describe/sounds/
        sounds_to_describe_idx = [0]
        resp = self.client.post('/home/describe/', {
            'describe': ['Describe selected files'],
            'sound-files': [f'file{idx}' for idx in sounds_to_describe_idx],  # Note this is not the filename but the value of the "select" option
        })
        self.assertRedirects(resp, '/home/describe/sounds/')
        self.assertEqual(self.client.session['len_original_describe_edit_sounds'], len(sounds_to_describe_idx))
        self.assertListEqual(sorted([os.path.basename(f.full_path) for f in self.client.session['describe_sounds']]), sorted([filenames[idx] for idx in sounds_to_describe_idx]))
        
        # Selecting multiple file redirects to /home/describe/license/
        sounds_to_describe_idx = [1, 2, 3]
        resp = self.client.post('/home/describe/', {
            'describe': ['Describe selected files'],
            'sound-files': [f'file{idx}' for idx in sounds_to_describe_idx],  # Note this is not the filename but the value of the "select" option
        })
        self.assertRedirects(resp, '/home/describe/license/')
        self.assertEqual(self.client.session['len_original_describe_edit_sounds'], len(sounds_to_describe_idx))
        self.assertListEqual(sorted([os.path.basename(f.full_path) for f in self.client.session['describe_sounds']]), sorted([filenames[idx] for idx in sounds_to_describe_idx]))
        
        # Selecting files to delete, redirect to delete confirmation
        sounds_to_delete_idx = [1, 2, 3]
        resp = self.client.post('/home/describe/', {
            'delete': ['Delete selected files'],
            'sound-files': [f'file{idx}' for idx in sounds_to_delete_idx],  # Note this is not the filename but the value of the "select" option,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertListEqual(sorted(resp.context['filenames']), sorted([filenames[idx] for idx in sounds_to_describe_idx]))

        # Selecting confirmation of files to delete
        resp = self.client.post('/home/describe/', {
            'delete_confirm': ['delete_confirm'],
            'sound-files': [f'file{idx}' for idx in sounds_to_delete_idx],  # Note this is not the filename but the value of the "select" option,
        })
        self.assertRedirects(resp, '/home/describe/')
        self.assertEqual(len(os.listdir(user_upload_path)), len(filenames) - len(sounds_to_delete_idx))

    @override_uploads_path_with_temp_directory
    def test_describe_selected_files(self):
        # Create audio files
        filenames = ['file1.wav', 'filè2.wav']
        user = User.objects.create_user("testuser", password="testpass")
        existing_pack = Pack.objects.create(user=user, name="existing pack")
        # Set is_whitelisted because this will trigger change_moderation_state after creating sound and make 
        # the test more complete
        user.profile.is_whitelisted = True
        user.profile.save()
        self.client.force_login(user)
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(filenames, user_upload_path)

        # Set license and pack data in session
        session = self.client.session
        session['describe_license'] = License.objects.all()[0]
        session['describe_pack'] = False
        session['describe_sounds'] = [File(1, filenames[0], user_upload_path + filenames[0], False),
                                      File(2, filenames[1], user_upload_path + filenames[1], False)]
        session.save()

        # Post description information
        resp = self.client.post('/home/describe/sounds/', {
            'submit': ['Submit and continue'],
            '0-lat': ['46.31658418182218'],
            '0-lon': ['3.515625'],
            '0-zoom': ['16'],
            '0-tags': ['testtag1 testtag2 testtag3'],
            '0-pack': [f'{existing_pack.id}'],
            '0-license': ['3'],
            '0-description': ['a test description for the sound file'],
            '0-new_pack': [''],
            '0-name': [filenames[0]],
            '1-license': ['3'],
            '1-description': ['another test description'],
            '1-lat': [''],
            '1-pack': [''],
            '1-lon': [''],
            '1-name': [filenames[1]],
            '1-new_pack': ['Name of a new pack'],
            '1-zoom': [''],
            '1-tags': ['testtag1 testtag4 testtag5'],
        })
        print(resp.content, resp.cookies['messages'].value)
        # Check that post redirected to first describe page with confirmation message on sounds described
        self.assertRedirects(resp, '/home/describe/')
        self.assertEqual('You have described all the selected files' in resp.cookies['messages'].value, True)

        # Check that sounds have been created along with related tags, geotags and packs
        self.assertEqual(user.sounds.all().count(), 2)
        self.assertListEqual(
            sorted(list(user.sounds.values_list('original_filename', flat=True))), 
            sorted([f for f in filenames]))
        self.assertEqual(Pack.objects.filter(name='Name of a new pack').exists(), True)
        self.assertEqual(Tag.objects.filter(name__contains="testtag").count(), 5)
        self.assertNotEqual(user.sounds.get(original_filename=filenames[0]).geotag, None)

    @override_uploads_path_with_temp_directory
    def test_describe_selected_files_bw(self):
        # NOTE: because BW ui uses different views/templates for sound description, we write a complementary
        # test for it

        # Create audio files
        filenames = ['file1.wav', 'filè2.wav']
        user = User.objects.create_user("testuser", email="1@xmpl.com", password="testpass")
        self.client.force_login(user)
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(filenames, user_upload_path)
        _, _, sound_sources = create_user_and_sounds(
            num_sounds=3, num_packs=0, 
            user=User.objects.create_user("testuser2", email="2@xmpl.com", password="testpass"))  # These sounds will be used as sources for an uploaded sound

        # Set license and pack data in session
        session = self.client.session
        session['describe_license'] = License.objects.all()[0]
        session['describe_pack'] = False
        session['len_original_describe_edit_sounds'] = 2
        session['describe_sounds'] = [File(1, filenames[0], user_upload_path + filenames[0], False),
                                      File(2, filenames[1], user_upload_path + filenames[1], False)]
        session.save()

        # Set BW frontend in session
        test_using_bw_ui(self)

        # Post description information
        resp = self.client.post('/home/describe/sounds/', {
            '0-lat': ['46.31658418182218'],
            '0-lon': ['3.515625'],
            '0-zoom': ['16'],
            '0-tags': ['testtag1 testtag2 testtag3'],
            '0-pack': [''],
            '0-license': ['3'],
            '0-description': ['a test description for the sound file'],
            '0-new_pack': [''],
            '0-name': [filenames[0]],
            '1-license': ['3'],
            '1-description': ['another test description'],
            '1-lat': [''],
            '1-pack': [''],
            '1-lon': [''],
            '1-name': [filenames[1]],
            '1-new_pack': ['Name of a new pack'],
            '1-zoom': [''],
            '1-tags': ['testtag1 testtag4 testtag5'],
            '1-sources': ','.join([f'{s.id}' for s in sound_sources]),
        })
        
        # Check that post redirected to first describe page with confirmation message on sounds described
        self.assertRedirects(resp, '/home/sounds/manage/')
        self.assertEqual('Successfully finished sound description round' in resp.cookies['messages'].value, True)

        # Check that sounds have been created along with related tags, geotags and packs
        self.assertEqual(user.sounds.all().count(), 2)
        self.assertListEqual(
            sorted(list(user.sounds.values_list('original_filename', flat=True))), 
            sorted([f for f in filenames]))
        self.assertEqual(Pack.objects.filter(name='Name of a new pack').exists(), True)
        self.assertEqual(Tag.objects.filter(name__contains="testtag").count(), 5)
        self.assertNotEqual(user.sounds.get(original_filename=filenames[0]).geotag, None)
        sound_with_sources = user.sounds.get(original_filename=filenames[1])
        self.assertEqual(sound_with_sources.sources.all().count(), len(sound_sources))


class BulkDescribe(TestCase):
    fixtures = ['licenses', 'user_groups']

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=40)
    def test_can_do_bulk_describe(self):
        user = User.objects.create_user("testuser")

        # Newly created user can't do bulk upload
        self.assertFalse(user.profile.can_do_bulk_upload())

        # When user has uploaded BULK_UPLOAD_MIN_SOUNDS, now she can bulk upload
        user.profile.num_sounds = settings.BULK_UPLOAD_MIN_SOUNDS
        self.assertTrue(user.profile.can_do_bulk_upload())

        # If user is whitelisted, she can bulk upload
        user.profile.refresh_from_db()
        self.assertFalse(user.profile.can_do_bulk_upload())
        user.profile.is_whitelisted = True
        self.assertTrue(user.profile.can_do_bulk_upload())

        # If user is assigned the bulk_uploaders group then bulk upload is allowed
        user.profile.refresh_from_db()
        self.assertFalse(user.profile.can_do_bulk_upload())
        group = Group.objects.get(name="bulk_uploaders")
        user.groups.add(group)
        # Reload object from db to refresh permission's caches (Note that refresh_from_db() doesn't clear perms cache)
        user = User.objects.get(id=user.id)
        self.assertTrue(user.profile.can_do_bulk_upload())

    @override_csv_path_with_temp_directory
    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    @mock.patch('general.tasks.validate_bulk_describe_csv.delay')
    def test_upload_csv(self, submit_job):
        user = User.objects.create_user("testuser", password="testpass")
        self.client.force_login(user)

        # Test successful file upload and redirect
        filename = "file.csv"
        f = SimpleUploadedFile(filename, b"file_content")
        resp = self.client.post(reverse('accounts-describe'), {'bulk-csv_file': f})
        bulk = BulkUploadProgress.objects.get(user=user)
        self.assertRedirects(resp, reverse('accounts-bulk-describe', args=[bulk.id]))

        # Test really file exists
        self.assertEqual(os.path.exists(bulk.csv_path), True)

        # Test job is triggered
        submit_job.assert_called_once_with(bulk_upload_progress_object_id=bulk.id)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_view_permissions(self):
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="N", user=user, original_csv_filename="test.csv")

        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        expected_redirect_url = reverse('login') + '?next=%s' % reverse('accounts-bulk-describe',
                                                                                 args=[bulk.id])
        self.assertRedirects(resp, expected_redirect_url)  # If user not logged in, redirect to login page

        self.client.force_login(user)
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertEqual(resp.status_code, 200)  # After login, page loads normally (200 OK)

        User.objects.create_user("testuser2", password="testpass", email='another_email@example.com')
        self.client.login(username='testuser2', password='testpass')
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertEqual(resp.status_code, 404)  # User without permission (not owner of object) gets 404

        with self.settings(BULK_UPLOAD_MIN_SOUNDS=10):
            # Now user is not allowed to load the page as user.profile.can_do_bulk_upload() returns False
            self.client.force_login(user)
            resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]), follow=True)
            self.assertRedirects(resp, reverse('accounts-home'))
            self.assertContains(resp, 'Your user does not have permission to use the bulk describe')

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_validating(self):
        # Test that when BulkUploadProgress has not finished validation we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="N", user=user, original_csv_filename="test.csv")
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertContains(resp, 'The uploaded data file has not yet been validated')

    @mock.patch('general.tasks.bulk_describe.delay')
    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_finished_validation(self, submit_job):
        # Test that when BulkUploadProgress has finished validation we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="V", user=user, original_csv_filename="test.csv")
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertContains(resp, 'Validation results of the data file')

        # Test that chosing option to delete existing BulkUploadProgress really does it
        resp = self.client.post(reverse('accounts-bulk-describe', args=[bulk.id]) + '?action=delete')
        self.assertRedirects(resp, reverse('accounts-describe'))  # Redirects to describe page after delete
        self.assertEqual(BulkUploadProgress.objects.filter(user=user).count(), 0)

        # Test that chosing option to start describing files triggers bulk describe gearmnan job
        bulk = BulkUploadProgress.objects.create(progress_type="V", user=user, original_csv_filename="test.csv")
        resp = self.client.post(reverse('accounts-bulk-describe', args=[bulk.id]) + '?action=start')
        self.assertEqual(resp.status_code, 200)
        submit_job.assert_called_once_with(bulk_upload_progress_object_id=bulk.id)

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_description_in_progress(self):
        # Test that when BulkUploadProgress has started description and processing we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="S", user=user, original_csv_filename="test.csv")
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertContains(resp, 'Your sounds are being described and processed')

        # Test that when BulkUploadProgress has finished describing items but still is processing some sounds, we
        # show that info to the users. First we fake some data for the bulk object
        bulk.progress_type = 'F'
        bulk.validation_output = {
            'lines_ok': list(range(5)),  # NOTE: we only use the length of these lists, so we fill them with irrelevant data
            'lines_with_errors': list(range(2)),
            'global_errors': [],
        }
        bulk.description_output = {
            '1': 1,  # NOTE: we only use the length of the dict so we fill it with irrelevant values/keys
            '2': 2,
            '3': 3,
        }
        bulk.save()
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertContains(resp, 'Your sounds are being described and processed')

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
        self.assertContains(resp, 'The bulk description process has finished!')

    @override_settings(BULK_UPLOAD_MIN_SOUNDS=0)
    def test_bulk_describe_state_closed(self):
        # Test that when BulkUploadProgress object is closed we show correct info to users
        user = User.objects.create_user("testuser", password="testpass")
        bulk = BulkUploadProgress.objects.create(progress_type="C", user=user, original_csv_filename="test.csv")
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts-bulk-describe', args=[bulk.id]))
        self.assertContains(resp, 'This bulk description process is closed')
