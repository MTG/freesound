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
from sounds.models import Sound, Pack, License, Download
from donations.models import Donation, DonationsModalSettings
from shutil import copyfile
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
            sound = Sound.objects.create(
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

        copyfile(user_upload_path + filenames[0], user_upload_path + "copy.wav")

        license = License.objects.all()[0]
        sound_fields = {
            'name': 'new sound',
            'dest_path': user_upload_path + filenames[0],
            'license': license.name,
            'description': 'new sound',
            'tags': clean_and_split_tags('tag1, tag2, tag3'),
        }
        sound = utils.sound_upload.create_sound(user, sound_fields, process=False)
        self.assertEqual(user.sounds.all().count(), 1)

        #Now the file has been removed so it should fail
        try:
            sound = utils.sound_upload.create_sound(user, sound_fields, process=False)
        except utils.sound_upload.NoAudioException:
            # If we try to upload the same file again it shuld also fail
            sound_fields['dest_path'] = user_upload_path + "copy.wav"
            try:
                sound = utils.sound_upload.create_sound(user, sound_fields, process=False)
            except utils.sound_upload.AlreadyExistsException:
                pass

        self.assertEqual(user.sounds.all().count(), 1)

        #Upload file with geotag and pack
        sound_fields['dest_path'] = user_upload_path + filenames[1]
        sound_fields['geotag'] = '41.2222,31.0000,17'
        sound_fields['pack'] = 'new pack'
        sound_fields['name'] = filenames[1]
        sound = utils.sound_upload.create_sound(user, sound_fields, process=False)
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
