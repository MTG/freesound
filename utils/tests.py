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

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from utils.forms import filename_has_valid_extension
from utils.tags import clean_and_split_tags
from utils.text import clean_html
from utils.sound_upload import get_csv_lines, validate_input_csv_file, bulk_describe_from_csv, create_sound, \
    NoAudioException, AlreadyExistsException
from sounds.models import Sound, Pack, License, Download
from donations.models import Donation, DonationsModalSettings
import shutil
import datetime
import utils.downloads
import tempfile
import os


class UtilsTest(TestCase):

    fixtures = ['initial_data']

    def test_filename_has_valid_extension(self):
        cases = [
            ('filaneme.wav', True),
            ('filaneme.aiff', True),
            ('filaneme.aif', True),
            ('filaneme.mp3', True),
            ('filaneme.ogg', True),
            ('filaneme.flac', True),
            ('filaneme.xyz', False),
            ('wav', False),
        ]
        for filename, expected_result in cases:
            self.assertEqual(filename_has_valid_extension(filename), expected_result)

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

    @override_settings(UPLOADS_PATH=tempfile.mkdtemp())
    def test_upload_sounds(self):
        # create new sound files
        filenames = ['file1.wav', 'file2.wav']
        user = User.objects.create_user("testuser", password="testpass")
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.mkdir(user_upload_path)
        for filename in filenames:
            f = open(user_upload_path + filename, 'a')
            f.write(os.urandom(1024))  # Add random content to the file to avoid equal md5
            f.close()

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

    fixtures = ['initial_data']

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

    def test_clean_html(self):
        # Test if the text input contains allowed html tags
        # The only supported tags are : a, img, strong, b, em, li, u, p, br, blockquotea and code
        ret = clean_html(u'a b c d')
        self.assertEqual(u'a b c d', ret)

        # Also make sure links contains rel="nofollow"
        ret = clean_html(u'<a href="http://www.google.com" rel="squeek">google</a>')
        self.assertEqual(u'<a href="http://www.google.com" rel="nofollow">google</a>', ret)

        ret = clean_html(u'<a href="http://www.google.com">google</a>')
        self.assertEqual(u'<a href="http://www.google.com" rel="nofollow">google</a>', ret)

        ret = clean_html(u'<h1>this should return the <strong>substring</strong> just <b>fine</b></h1>')
        self.assertEqual(u'this should return the <strong>substring</strong> just <b>fine</b>', ret)

        ret = clean_html(u'<table><tr><td>amazing</td><td>grace</td></tr></table>')
        self.assertEqual(u'amazinggrace', ret)

        ret = clean_html(u'<a href="javascript:void(0)">click me</a>')
        self.assertEqual(u'click me', ret)

        ret = clean_html(u'<p class="hello">click me</p>')
        self.assertEqual(u'<p>click me</p>', ret)

        ret = clean_html(u'<a></a>')
        self.assertEqual(u'', ret)

        ret = clean_html(u'<a>hello</a>')
        self.assertEqual(u'hello', ret)

        ret = clean_html(u'<p class="hello" id="1">a<br/>b<br/></a>')
        self.assertEqual(u'<p>a<br>b<br></p>', ret)

        ret = clean_html(u'<p></p>')
        self.assertEqual(u'<p></p>', ret)

        ret = clean_html(u'<A REL="nofollow" hREF="http://www.google.com"><strong>http://www.google.com</strong></a>')
        self.assertEqual(u'<a href="http://www.google.com" rel="nofollow"><strong>http://www.google.com</strong></a>', ret)

        ret = clean_html(u'<a rel="nofollow" href="http://www.google.com"><strong>http://www.google.com</strong></a>')
        self.assertEqual(u'<a href="http://www.google.com" rel="nofollow"><strong>http://www.google.com</strong></a>', ret)

        ret = clean_html(u'http://www.google.com <a href="">http://www.google.com</a>')
        self.assertEqual(u'<a href="http://www.google.com" rel="nofollow">http://www.google.com</a> <a href="http://www.google.com" rel="nofollow">http://www.google.com</a>', ret)

        ret = clean_html(u'<ul><p id=5><a href="123">123</a>hello<strong class=156>there http://www.google.com</strong></p></ul>')
        self.assertEqual(u'<ul><p>123hello<strong>there <a href="http://www.google.com" rel="nofollow">http://www.google.com</a></strong></p></ul>', ret)

        ret = clean_html(u'abc http://www.google.com abc')
        self.assertEqual(u'abc <a href="http://www.google.com" rel="nofollow">http://www.google.com</a> abc', ret)

        # The links inside <> are encoded by &lt; and &gt;
        ret = clean_html(u'abc <http://www.google.com> abc')
        self.assertEqual(u'abc &lt; <a href="http://www.google.com" rel="nofollow">http://www.google.com</a> &gt; abc', ret)

        ret = clean_html(u'GALORE: https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092\\nFreesound Moderator')
        self.assertEqual(u'GALORE: <a href="https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092" rel="nofollow">https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092</a>\\nFreesound Moderator', ret)

        # Allow custom placeholders
        ret = clean_html(u'<a href="${sound_id}">my sound id</a>')
        self.assertEqual(u'<a href="${sound_id}" rel="nofollow">my sound id</a>', ret)

        ret = clean_html(u'<a href="${sound_url}">my sound url</a>')
        self.assertEqual(u'<a href="${sound_url}" rel="nofollow">my sound url</a>', ret)

        ret = clean_html(u'<img src="https://freesound.org/media/images/logo.png">')
        self.assertEqual(u'<img src="https://freesound.org/media/images/logo.png">', ret)

        ret = clean_html(u'<ul><li>Some list</li></ul>')
        self.assertEqual(u'<ul><li>Some list</li></ul>', ret)


class BulkDescribeUtils(TestCase):

    fixtures = ['initial_data']

    @staticmethod
    def create_audio_files(filenames, base_path):
        for filename in filenames:
            f = open(base_path + filename, 'a')
            f.write(os.urandom(1024))  # Add random content to the file to avoid equal md5
            f.close()

    @staticmethod
    def create_csv_file(filename, lines, base_path):
        csv_file_path = '%s/%s' % (base_path, filename)
        csv_fid = open(csv_file_path, 'w')
        for line in lines:
            csv_fid.write(line + '\n')
        csv_fid.close()
        return csv_file_path

    @override_settings(UPLOADS_PATH=tempfile.mkdtemp())
    @override_settings(CSV_PATH=tempfile.mkdtemp())
    def test_validate_input_csv_file(self):
        # Create user uploads folder and test audio files
        user = User.objects.create_user("testuser", password="testpass")
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.mkdir(user_upload_path)
        self.create_audio_files(['file1.wav', 'file2.wav', 'file3.wav', 'file4.wav', 'file5.wav'], user_upload_path)

        # Create CSV files folder with descriptions
        csv_file_base_path = settings.CSV_PATH + '/%i/' % user.id
        os.mkdir(csv_file_base_path)

        # Test CSV with all lines and metadata ok
        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;pack_name;is_explicit',
            'file1.wav;New name for file1.wav;tag1 tag2 tag3;41.4065, 2.19504, 23;'
            '"Description for file";Creative Commons 0;ambient;0',  # All fields valid
            'file2.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;0',  # Only mandatory fields
            'file3.wav;;tag1 tag2 tag3;;'
            '"Description for file";Creative Commons 0;ambient;1',  # All mandatory fields and some optional fields
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
        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;pack_name;is_explicit',
            'file1.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;1',  # File exists, fields ok
            'file2.wav;;tag1 tag2 tag3;;;Creative Commons 0;;1',  # Missing description
            'file3.wav;;tag1 tag2 tag3;;"Description for file";;1',  # Wrong number of columns
            'file6.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;1',  # Audiofile does not exist
            'file2.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;1',  # Audiofile already described
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
        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;pack_name;is_explicit',
            'file1.wav;;tag1 tag2;;"Description for file";Creative Commons 0;;1',  # Wrong tags (less than 3)
            'file2.wav;;tag1,tag2;;"Description for file";Creative Commons 0;;1',  # Wrong tags (less than 3)
            'file3.wav;;tag1,tag2;gr87g;"Description for file2";Creative Commons 0;;1',  # Wrong geotag
            'file4.wav;;tag1,tag2;42.34,190.45,15;"Description for file";Creative Commons 0;;1',  # Wrong geotag
            'file5.wav;;tag1 tag2 tag3;;"Description for file";Sampling+;;1',  # Invalid license
            'file6.wav;;tag1 tag2 tag3;;"Description for file";Sampling+;;rt',  # Invalid is_explicit
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
        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;unknown_field',
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path, username=user.username)
        self.assertEqual(len(global_errors), 2)  # Two global errors
        self.assertTrue('Invalid header' in global_errors[0])  # Invalid header error reported
        self.assertTrue('no lines with sound' in global_errors[1])  # No sounds in csv file error reported

        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;pack_name;is_explicit',
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path,
                                    username=None)  # Not passing username, header should now include 'username' field
        self.assertEqual(len(global_errors), 2)  # One global error
        self.assertTrue('Invalid header' in global_errors[0])  # Invalid header error reported
        self.assertTrue('no lines with sound' in global_errors[1])  # No sounds in csv file error reported

        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;pack_name;is_explicit;username',
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = \
            validate_input_csv_file(header, lines, user_upload_path,
                                    username=None)  # Not passing username, header should now include 'username' field
        self.assertEqual(len(global_errors), 1)  # One global error
        self.assertTrue('no lines with sound' in global_errors[0])  # No sounds in csv file error reported

        # Test username errors when not passing username argument to validate_input_csv_file
        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;pack_name;is_explicit;username',
            'file1.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;1;new_username',  # User does not exist
            'file2.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;1',  # Invlaid num columns
            'file3.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;0;testuser',  # All fields OK
        ], csv_file_base_path)
        header, lines = get_csv_lines(csv_file_path)
        lines_validated, global_errors = validate_input_csv_file(header, lines, user_upload_path, username=None)
        self.assertEqual(len(global_errors), 0)  # No global errors
        self.assertEqual(len([line for line in lines_validated if line['line_errors']]), 2)  # Two lines have errors
        self.assertTrue('username' in lines_validated[0]['line_errors'])  # User does not exist
        self.assertTrue('columns' in lines_validated[1]['line_errors'])  # Invalid number of columns

        # Delete tmp directories
        shutil.rmtree(settings.UPLOADS_PATH)
        shutil.rmtree(settings.CSV_PATH)

    @override_settings(UPLOADS_PATH=tempfile.mkdtemp())
    @override_settings(CSV_PATH=tempfile.mkdtemp())
    def test_bulk_describe_from_csv(self):

        # Create user uploads folder and test audio files
        user = User.objects.create_user("testuser", password="testpass")
        user_upload_path = settings.UPLOADS_PATH + '/%i/' % user.id
        os.mkdir(user_upload_path)
        self.create_audio_files(['file1.wav', 'file2.wav', 'file3.wav', 'file4.wav', 'file5.wav'], user_upload_path)

        # Create CSV files folder with descriptions
        csv_file_base_path = settings.CSV_PATH + '/%i/' % user.id
        os.mkdir(csv_file_base_path)

        # Create Test CSV with some lines ok and some wrong lines
        csv_file_path = self.create_csv_file('test_descriptions.csv', [
            'audio_filename;name;tags;geotag;description;license;pack_name;is_explicit',
            'file1.wav;;tag1 tag2 tag3;41.4065, 2.19504, 23;"Description for file";Creative Commons 0;ambient;1',  # OK
            'file2.wav;;tag1 tag2 tag3;;"Description for file";Invalid license;;1',  # Invalid license
            'file3.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;1',  # Wrong number of columns
            'file4.wav;;tag1 tag2 tag3;dg;"Description for file";Creative Commons 0;;0',  # Invalid geotag
            'file5.wav;;tag1 tag2 tag3;;"Description for file";Creative Commons 0;;0',  # OK
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
        self.assertEquals(sound1.pack.name, 'ambient')  # Check sound has pack and name of pack is 'ambient'
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

        # Delete tmp directories
        shutil.rmtree(settings.UPLOADS_PATH)
        shutil.rmtree(settings.CSV_PATH)
