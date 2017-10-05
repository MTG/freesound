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

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings, Client
from django.test.utils import override_settings, skipIf
from django.contrib.auth.models import User, Permission
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.sites.models import Site
from django.urls import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.core import mail
from django.conf import settings
from accounts.models import Profile, EmailPreferenceType, SameUser, ResetEmailRequest
from accounts.views import handle_uploaded_image
from accounts.forms import FsPasswordResetForm
from sounds.models import License, Sound, Pack, DeletedSound, SoundOfTheDay
from tags.models import TaggedItem
from utils.filesystem import File
from tags.models import Tag
from comments.models import Comment
from forum.models import Thread, Post, Forum
from tickets.models import Ticket
import accounts.models
import mock
import os
import tempfile
import shutil
import datetime
from utils.mail import transform_unique_email, replace_email_to


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

    def test_random_sound_response_ok(self):
        # 302 response on random sound access
        resp = self.client.get(reverse('sounds-random'))
        self.assertEqual(resp.status_code, 302)

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

        # 200 response on wiki developers page
        resp = self.client.get(reverse('wiki_developers'))
        self.assertEqual(resp.status_code, 302)

        # 200 response on forums moderation page
        resp = self.client.get(reverse('forums-moderate'))
        self.assertEqual(resp.status_code, 200)

    def test_username_check(self):
        username = 'test_user'
        resp = self.client.post(reverse('check_username'),
                {'username': username})
        self.assertEqual(resp.status_code, 200)

        User.objects.create_user(username, password="testpass")
        resp = self.client.post(reverse('check_username'),
                {'username': username})
        self.assertEqual(resp.status_code, 200)


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
            'profile-about': 'About test text',
            'profile-signature': 'Signature test text',
            'profile-not_shown_in_online_users_list': True,
        })

        user = User.objects.select_related('profile').get(username="testuser")
        self.assertEqual(user.profile.home_page, 'http://www.example.com/')
        self.assertEqual(user.profile.about, 'About test text')
        self.assertEqual(user.profile.signature, 'Signature test text')
        self.assertEqual(user.profile.not_shown_in_online_users_list, True)

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
            'files': [u'file1'],
        })
        self.assertRedirects(resp, '/home/describe/sounds/')

        # Selecting multiple file redirects to /home/describe/license/
        resp = self.client.post('/home/describe/', {
            'describe': [u'Describe selected files'],
            'files': [u'file1', u'file0'],
        })
        self.assertRedirects(resp, '/home/describe/license/')

        # Selecting files to delete, redirecte to delete confirmation
        filenames_to_delete = [u'file1', u'file0']
        resp = self.client.post('/home/describe/', {
            'delete': [u'Delete selected files'],
            'files': filenames_to_delete,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['filenames']), len(filenames_to_delete))

        # Selecting confirmation of files to delete
        resp = self.client.post('/home/describe/', {
            'delete_confirm': [u'delete_confirm'],
            'files': filenames_to_delete,
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

    def test_user_delete_remove_sounds(self):
        # This should set user's attribute deleted_user to True and anonymize it,
        # also should remove users Sounds and Packs, and create DeletedSound
        # objects
        user = self.create_user_and_content()
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

    def test_replace_when_sending_email(self):

        @replace_email_to
        def fake_send_email(subject, email_body, email_from, email_to, reply_to=None):
            return email_to

        # Check that emails sent to user_a are sent to his address
        used_email_to = fake_send_email('Test subject', 'Test body', email_to=[self.user_a.email])
        self.assertEquals(used_email_to[0], self.user_a.email)

        # For user b, email_to also remains the same
        used_email_to = fake_send_email('Test subject', 'Test body', email_to=[self.user_b.email])
        self.assertEquals(used_email_to[0], self.user_b.email)

        # For user c, email_to changes according to SameUser table
        used_email_to = fake_send_email('Test subject', 'Test body', email_to=[self.user_c.email])
        self.assertEquals(used_email_to[0], self.user_b.email)  # email_to becomes user_b.email

        # If we remove SameUser entries, email of user_c is not replaced anymore
        SameUser.objects.all().delete()
        used_email_to = fake_send_email('Test subject', 'Test body', email_to=[self.user_c.email])
        self.assertEquals(used_email_to[0], self.user_c.email)

        # Test with email_to not being a list or tuple
        used_email_to = fake_send_email('Test subject', 'Test body', email_to=self.user_a.email)
        self.assertEquals(used_email_to[0], self.user_a.email)

        # Test with email_to being empty ''
        used_email_to = fake_send_email('Test subject', 'Test body', email_to='')
        self.assertEquals(used_email_to, True)

        # Test with email_to being None, should return admin emails
        used_email_to = fake_send_email('Test subject', 'Test body', email_to=None)
        admin_emails = [admin[1] for admin in settings.SUPPORT]
        self.assertEquals(used_email_to[0], admin_emails[0])


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

