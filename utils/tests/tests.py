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

from builtins import range
import datetime
import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

import utils.downloads
from donations.models import Donation, DonationsModalSettings
from sounds.models import Sound, Pack, License, Download
from utils.audioprocessing.freesound_audio_processing import FreesoundAudioProcessor
from utils.audioprocessing.processing import AudioProcessingException
from utils.sound_upload import get_csv_lines, validate_input_csv_file, bulk_describe_from_csv, create_sound, \
    NoAudioException, AlreadyExistsException
from utils.tags import clean_and_split_tags
from utils.test_helpers import create_test_files, create_user_and_sounds, override_uploads_path_with_temp_directory, \
    override_csv_path_with_temp_directory, override_sounds_path_with_temp_directory, \
    override_previews_path_with_temp_directory, override_displays_path_with_temp_directory, \
    override_processing_tmp_path_with_temp_directory


class UtilsTest(TestCase):

    fixtures = ['licenses', 'user_groups', 'moderation_queues']

    def test_download_sounds(self):
        user = User.objects.create_user("testuser", password="testpass")
        pack = Pack.objects.create(user=user, name="Test pack")
        for i in range(0, 5):
            Sound.objects.create(
                user=user,
                original_filename="Test sound %i" % i,
                base_filename_slug="test_sound_%i" % i,
                license=License.objects.all()[0],
                pack=pack,
                md5="fakemd5_%i" % i)
        licenses_url = (reverse('pack-licenses', args=["testuser", pack.id]))
        ret = utils.downloads.download_sounds(licenses_url, pack)
        self.assertEqual(ret.status_code, 200)

    @override_uploads_path_with_temp_directory
    def test_upload_sounds(self):
        # create new sound files
        filenames = ['file1.wav', 'file2.wav']
        user = User.objects.create_user("testuser", password="testpass")
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(filenames, user_upload_path)
        shutil.copyfile(user_upload_path + filenames[0], user_upload_path + "copy.wav")
        license = License.objects.all()[0]
        sound_fields = {
            'name': 'new sound',
            'dest_path': user_upload_path + filenames[0],
            'license': license.name,
            'description': 'new sound',
            'tags': clean_and_split_tags('tag1, tag2, tag3'),
        }
        create_sound(user, sound_fields, process=False)
        self.assertEqual(user.sounds.all().count(), 1)

        # Now the file has been removed so it should fail
        try:
            create_sound(user, sound_fields, process=False)
        except NoAudioException:
            # If we try to upload the same file again it shuld also fail
            sound_fields['dest_path'] = user_upload_path + "copy.wav"
            try:
                create_sound(user, sound_fields, process=False)
            except AlreadyExistsException:
                pass
        self.assertEqual(user.sounds.all().count(), 1)

        # Upload file with geotag and pack
        sound_fields['dest_path'] = user_upload_path + filenames[1]
        sound_fields['geotag'] = '41.2222,31.0000,17'
        sound_fields['pack'] = 'new pack'
        sound_fields['name'] = filenames[1]
        create_sound(user, sound_fields, process=False)
        self.assertEqual(user.sounds.all().count(), 2)
        self.assertEqual(Pack.objects.filter(name='new pack').exists(), True)
        self.assertEqual(user.sounds.get(original_filename=filenames[1]).tags.count(), 3)
        self.assertNotEqual(user.sounds.get(original_filename=filenames[1]).geotag, None)


class ShouldSuggestDonationTest(TestCase):

    fixtures = ['licenses']

    def test_should_suggest_donation_probabilty_1(self):

        # In this set of tests 'should_suggest_donation' should return True or False depending on the decided criteria
        # Probabilty is set to 1.0 to avoid ranomeness in the test
        donations_settings, _ = DonationsModalSettings.objects.get_or_create()
        donations_settings.display_probability = 1.0
        donations_settings.save()
        cache.set(DonationsModalSettings.DONATION_MODAL_SETTINGS_CACHE_KEY, donations_settings, timeout=3600)

        user = User.objects.create_user("testuser", password="testpass")

        # should_suggest_donation returns False if modal has been shown more than DONATION_MODAL_DISPLAY_TIMES_DAY
        times_shown_in_last_day = donations_settings.max_times_display_a_day + 1
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)

        # set times_shown_in_last_day lower than DONATION_MODAL_DISPLAY_TIMES_DAY
        times_shown_in_last_day = donations_settings.max_times_display_a_day - 1

        # if user donated recently, modal is not shown (even if times_shown_in_last_day <
        # DONATION_MODAL_DISPLAY_TIMES_DAY)
        donation = Donation.objects.create(user=user, amount=1)
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)

        # remove donation object (to simulate user never donated)
        donation.delete()

        # if user has downloaded less or equal than donations_settings.downloads_in_period, do not show the modal
        sound = Sound.objects.create(
            user=user,
            original_filename="Test sound",
            base_filename_slug="test_sound_10",
            license=License.objects.all()[0],
            md5="fakemd5_10")
        for i in range(0, donations_settings.downloads_in_period):
            Download.objects.create(user=user, sound=sound, license=License.objects.first())
            self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)
        Download.objects.create(user=user, sound=sound, license=License.objects.first())  # downloads > donations_settings.downloads_in_period (modal shows)
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), True)

        # if the download objects are older than donations_settings.download_days, don't consider them
        Download.objects.filter(user=user).update(
            created=datetime.datetime.now()-datetime.timedelta(days=donations_settings.download_days + 1))
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)

        # if user has donations but these are older than donations_settings.days_after_donation, do not consider them
        Donation.objects.create(user=user, amount=1)
        Donation.objects.filter(user=user).update(
            created=datetime.datetime.now()-datetime.timedelta(days=donations_settings.days_after_donation + 1))
        Download.objects.filter(user=user).update(
            created=datetime.datetime.now())  # Change downloads date again to be recent (modal show be shown)
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), True)

    def test_should_suggest_donation_probabilty_0(self):
        # In this set of tests 'should_suggest_donation' should always return False as probability is set to 0.0
        donations_settings, _ = DonationsModalSettings.objects.get_or_create()
        donations_settings.display_probability = 0.0
        donations_settings.save()
        cache.set(DonationsModalSettings.DONATION_MODAL_SETTINGS_CACHE_KEY, donations_settings, timeout=3600)

        user = User.objects.create_user("testuser", password="testpass")

        # should_suggest_donation returns False if modal has been shown more than DONATION_MODAL_DISPLAY_TIMES_DAY
        times_shown_in_last_day = donations_settings.max_times_display_a_day + 1
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)

        # set times_shown_in_last_day lower than DONATION_MODAL_DISPLAY_TIMES_DAY
        times_shown_in_last_day = donations_settings.max_times_display_a_day - 1

        # if user donated recently, modal is not shown (even if times_shown_in_last_day <
        # DONATION_MODAL_DISPLAY_TIMES_DAY)
        donation = Donation.objects.create(user=user, amount=1)
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)

        # remove donation object (to simulate user never donated)
        donation.delete()

        # if user has downloaded less or equal than donations_settings.downloads_in_period, do not show the modal
        sound = Sound.objects.create(
            user=user,
            original_filename="Test sound",
            base_filename_slug="test_sound_10",
            license=License.objects.all()[0],
            md5="fakemd5_10")
        for i in range(0, donations_settings.downloads_in_period):
            Download.objects.create(user=user, sound=sound, license=License.objects.first())
            self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)
        Download.objects.create(user=user, sound=sound, license=License.objects.first())  # n downloads > donations_settings.downloads_in_period
        # In this case still not shown the modal as probability is 0.0
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)

        # if the download objects are older than donations_settings.download_days, don't consider them
        Download.objects.filter(user=user).update(
            created=datetime.datetime.now() - datetime.timedelta(days=donations_settings.download_days + 1))
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)

        # if user has donations but these are older than donations_settings.days_after_donation, do not consider them
        Donation.objects.create(user=user, amount=1)
        Donation.objects.filter(user=user).update(
            created=datetime.datetime.now() - datetime.timedelta(days=donations_settings.days_after_donation + 1))
        Download.objects.filter(user=user).update(
            created=datetime.datetime.now())
        # Change downloads date again to be recent (however modal won't show because probability is 0.0)
        self.assertEqual(utils.downloads.should_suggest_donation(user, times_shown_in_last_day), False)


class BulkDescribeUtils(TestCase):

    fixtures = ['licenses']

    @staticmethod
    def create_file_with_lines(filename, lines, base_path):
        csv_file_path = '%s/%s' % (base_path, filename)
        csv_fid = open(csv_file_path, 'w')
        for line in lines:
            csv_fid.write(line + '\n')
        csv_fid.close()
        return csv_file_path

    def test_get_csv_lines(self):
        # Load sample files for CSV, XLS and XLSX formats and compare the output of reading them is the same
        sample_csv_path = os.path.join(settings.MEDIA_ROOT, 'sample.csv')
        sample_xls_path = os.path.join(settings.MEDIA_ROOT, 'sample.xls')
        sample_xlsx_path = os.path.join(settings.MEDIA_ROOT, 'sample.xlsx')
        header_csv, lines_csv = get_csv_lines(sample_csv_path)
        header_xls, lines_xls = get_csv_lines(sample_xls_path)
        header_xlsx, lines_xlsx = get_csv_lines(sample_xlsx_path)

        for i in range(0, len(header_csv)):
            # Check headers have the same value
            self.assertTrue(header_csv[i] == header_xls[i] == header_xlsx[i])

            # Check lines from all formats parse same value for specific header value
            header_value = header_csv[i]
            for j in range(0, len(lines_csv)):
                if header_value == 'is_explicit':
                    # NOTE: Excel treats all numbers as floats, therefore for comparing rows that have numbers we
                    # first convert them all to float.
                    self.assertTrue(
                        float(lines_csv[j][header_value]) ==
                        float(lines_xls[j][header_value]) ==
                        float(lines_xlsx[j][header_value]))
                else:
                    self.assertTrue(
                        lines_csv[j][header_value] ==
                        lines_xls[j][header_value] ==
                        lines_xlsx[j][header_value])

        # NOTE: more advance testing of this funciton would mean testing with different types of "good" and "bad" files
        # for each of the formats. For the CSV case that would rather feasible as we can generate the files
        # programatically. For the XLS and XLSX case we would need to rely on a third-party library to create XLS and
        # XLSX files which would only be used for that. In any of the cases, we will never cover the myriard of
        # evil CSV/XLS/XLSX files that can be out there. I think it is better to make sure that in case of unexpected
        # error we show that message to the users instead of trying to cover all possible errors.

    @override_uploads_path_with_temp_directory
    @override_csv_path_with_temp_directory
    def test_validate_input_csv_file(self):
        # Create user uploads folder and test audio files
        user = User.objects.create_user("testuser", password="testpass")
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(['file1.wav', 'file2.wav', 'file3.wav', 'file4.wav', 'file5.wav'], user_upload_path)

        # Create CSV files folder with descriptions
        csv_file_base_path = settings.CSV_PATH + '/%i/' % user.id
        os.makedirs(csv_file_base_path, exist_ok=True)

        # Test CSV with all lines and metadata ok
        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,pack_name,is_explicit',
            'file1.wav,New name for file1.wav,"tag1 tag2 tag3","41.4065, 2.19504, 23",'
            '"Description for file",Creative Commons 0,ambient,0',  # All fields valid
            'file2.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,0',  # Only mandatory fields
            'file3.wav,,"tag1 tag2 tag3",,'
            '"Description for file",Creative Commons 0,ambient,1',  # All mandatory fields and some optional fields
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path, username=user.username)
        self.assertEqual(len(global_errors), 0)  # No global errors
        self.assertEqual(len([line for line in lines_validated if line['line_errors']]), 0)  # No line errors

        # Test username does not exist
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path, username="unexisting username")
        self.assertEqual(len(global_errors), 0)  # No global errors
        self.assertEqual(len([line for line in lines_validated if line['line_errors']]), 3)  # Three line errors
        self.assertTrue('username' in lines_validated[0]['line_errors'])  # User does not exist error reported
        self.assertTrue('username' in lines_validated[1]['line_errors'])  # User does not exist error reported
        self.assertTrue('username' in lines_validated[2]['line_errors'])  # User does not exist error reported

        # Test missing/duplicated audiofile and wrong number of rows
        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,pack_name,is_explicit',
            'file1.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,1',  # File exists, fields ok
            'file2.wav,,"tag1 tag2 tag3",,,Creative Commons 0,,1',  # Missing description
            'file3.wav,,"tag1 tag2 tag3",,"Description for file",,1',  # Wrong number of columns
            'file6.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,1',  # Audiofile does not exist
            'file2.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,1',  # Audiofile already described
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path, username=user.username)
        self.assertEqual(len(global_errors), 0)  # No global errors
        self.assertEqual(len([line for line in lines_validated if line['line_errors']]), 4)  # Four lines have errors
        self.assertTrue('description' in lines_validated[1]['line_errors'])  # Missing description error reported
        self.assertTrue('columns' in lines_validated[2]['line_errors'])  # Wrong number of columns reported
        self.assertTrue('audio_filename' in lines_validated[3]['line_errors'])  # Audiofile not exist error reported
        self.assertTrue('audio_filename' in lines_validated[4]['line_errors'])  # File already described error reported

        # Test validation errors in individual fields
        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,pack_name,is_explicit',
            'file1.wav,,"tag1 tag2",,"Description for file",Creative Commons 0,,1',  # Wrong tags (less than 3)
            'file2.wav,,"tag1,tag2",,"Description for file",Creative Commons 0,,1',  # Wrong tags (less than 3)
            'file3.wav,,"tag1,tag2",gr87g,"Description for file2",Creative Commons 0,,1',  # Wrong geotag
            'file4.wav,,"tag1,tag2",42.34,190.45,15,"Description for file",Creative Commons 0,,1',  # Wrong geotag
            'file5.wav,,"tag1 tag2 tag3",,"Description for file",Sampling+,,1',  # Invalid license
            'file6.wav,,"tag1 tag2 tag3",,"Description for file",Sampling+,,rt',  # Invalid is_explicit
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path, username=user.username)
        self.assertEqual(len(global_errors), 0)  # No global errors
        self.assertEqual(len([line for line in lines_validated if line['line_errors']]), 6)  # Six lines have errors
        self.assertTrue('tags' in lines_validated[0]['line_errors'])  # Wrong tags
        self.assertTrue('tags' in lines_validated[1]['line_errors'])  # Wrong tags
        self.assertTrue('geotag' in lines_validated[2]['line_errors'])  # Wrong geotag
        self.assertTrue('geotag' in lines_validated[3]['line_errors'])  # Wrong geotag
        self.assertTrue('license' in lines_validated[4]['line_errors'])  # Wrong license
        self.assertTrue('is_explicit' in lines_validated[5]['line_errors'])  # Wrong is_explicit

        # Test wrong header global errors
        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,unknown_field',
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path, username=user.username)
        self.assertEqual(len(global_errors), 2)  # Two global errors
        self.assertTrue('Invalid header' in global_errors[0])  # Invalid header error reported
        self.assertTrue('no lines with sound' in global_errors[1])  # No sounds in csv file error reported

        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,pack_name,is_explicit',
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path,
                                    username=None)  # Not passing username, header should now include 'username' field
        self.assertEqual(len(global_errors), 2)  # One global error
        self.assertTrue('Invalid header' in global_errors[0])  # Invalid header error reported
        self.assertTrue('no lines with sound' in global_errors[1])  # No sounds in csv file error reported

        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,pack_name,is_explicit,username',
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path,
                                    username=None)  # Not passing username, header should now include 'username' field
        self.assertEqual(len(global_errors), 1)  # One global error
        self.assertTrue('no lines with sound' in global_errors[0])  # No sounds in csv file error reported

        # Test username errors when not passing username argument to validate_input_csv_file
        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,pack_name,is_explicit,username',
            'file1.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,1,new_username',  # User does not exist
            'file2.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,1',  # Invlaid num columns
            'file3.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,0,testuser',  # All fields OK
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = validate_input_csv_file(header, lines, user_upload_path, username=None)
        self.assertEqual(len(global_errors), 0)  # No global errors
        self.assertEqual(len([line for line in lines_validated if line['line_errors']]), 2)  # Two lines have errors
        self.assertTrue('username' in lines_validated[0]['line_errors'])  # User does not exist
        self.assertTrue('columns' in lines_validated[1]['line_errors'])  # Invalid number of columns

    @override_uploads_path_with_temp_directory
    @override_csv_path_with_temp_directory
    def test_bulk_describe_from_csv(self):

        # Create user uploads folder and test audio files
        user = User.objects.create_user("testuser", password="testpass")
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.makedirs(user_upload_path, exist_ok=True)
        create_test_files(['file1.wav', 'file2.wav', 'file3.wav', 'file4.wav', 'file5.wav'], user_upload_path)

        # Create CSV files folder with descriptions
        csv_file_base_path = settings.CSV_PATH + '/%i/' % user.id
        os.makedirs(csv_file_base_path, exist_ok=True)

        # Create Test CSV with some lines ok and some wrong lines
        csv_file_path = self.create_file_with_lines('test_descriptions.csv', [
            'audio_filename,name,tags,geotag,description,license,pack_name,is_explicit',
            'file1.wav,,"tag1 tag2 tag3","41.4065, 2.19504, 23","Description for file",Creative Commons 0,ambient,1',  # OK
            'file2.wav,,"tag1 tag2 tag3",,"Description for file",Invalid license,,1',  # Invalid license
            'file3.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,1',  # Wrong number of columns
            'file4.wav,,"tag1 tag2 tag3",dg,"Description for file",Creative Commons 0,,0',  # Invalid geotag
            'file5.wav,,"tag1 tag2 tag3",,"Description for file",Creative Commons 0,,0',  # OK
        ], csv_file_base_path)

        # Test case when no sounds are been created because CSV file has some errors and 'force_import' is set to False
        bulk_describe_from_csv(csv_file_path,
                               delete_already_existing=False,
                               force_import=False,
                               sounds_base_dir=user_upload_path,
                               username=user.username)
        self.assertEqual(user.sounds.count(), 0)  # User has no sounds

        # Test case using 'force_import' (only sounds for lines that validate ok will be created)
        bulk_describe_from_csv(csv_file_path,
                               delete_already_existing=False,
                               force_import=True,
                               sounds_base_dir=user_upload_path,
                               username=user.username)
        self.assertEqual(user.sounds.count(), 2)  # The two sounds that had correct metadata have been added
        sound1 = Sound.objects.get(user=user, original_filename='file1.wav')  # Get first correct sound
        sound1_id = sound1.id  # This is used in a test below
        self.assertTrue(sound1.geotag)  # Check sound has geotag object assigned
        self.assertEqual(sound1.pack.name, 'ambient')  # Check sound has pack and name of pack is 'ambient'
        sound2 = Sound.objects.get(user=user, original_filename='file5.wav')  # Get last correct sound
        sound2_id = sound2.id  # This is used in a test below
        self.assertIsNone(sound2.geotag)  # Check sound has no geotag
        self.assertIsNone(sound2.pack)  # Check sound has no pack

        # Run again using 'force_import' and sounds won't be created because sounds already exist and md5 check fails
        # NOTE: first we copy back the files that were already successfully added because otherwise these don't exist
        shutil.copy(sound1.locations()['path'], os.path.join(user_upload_path, 'file1.wav'))
        shutil.copy(sound2.locations()['path'], os.path.join(user_upload_path, 'file5.wav'))
        bulk_describe_from_csv(csv_file_path,
                               delete_already_existing=False,
                               force_import=True,
                               sounds_base_dir=user_upload_path,
                               username=user.username)
        self.assertEqual(user.sounds.count(), 2)  # User still has two sounds, no new sounds added

        # Run again using 'force_import' AND 'delete_already_existing' and existing sounds will be removed before
        # creating the new ones
        # NOTE: first we copy back the files that failed MD5 check as files are discarted (deleted) when MD5 fails
        shutil.copy(sound1.locations()['path'], os.path.join(user_upload_path, 'file1.wav'))
        shutil.copy(sound2.locations()['path'], os.path.join(user_upload_path, 'file5.wav'))
        bulk_describe_from_csv(csv_file_path,
                               delete_already_existing=True,
                               force_import=True,
                               sounds_base_dir=user_upload_path,
                               username=user.username)
        self.assertEqual(user.sounds.count(), 2)  # User still has two sounds
        new_sound1 = Sound.objects.get(user=user, original_filename='file1.wav')  # New version of first correct sound
        new_sound2 = Sound.objects.get(user=user, original_filename='file5.wav')  # New version of last correct sound
        self.assertNotEqual(new_sound1.id, sound1_id)  # Check that IDs are not the same
        self.assertNotEqual(new_sound2.id, sound2_id)  # Check that IDs are not the same
