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

from django.test import TestCase
from django.test.utils import override_settings, skipIf
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.conf import settings
from accounts.models import Profile
from accounts.views import handle_uploaded_image
from sounds.models import License, Sound, Pack, DeletedSound
from tags.models import TaggedItem
from utils.filesystem import File
from tags.models import Tag
from comments.models import Comment
from forum.models import Thread, Post, Forum
import accounts.models
import mock
import os
import tempfile
import shutil


class SimpleUserTest(TestCase):
    
    fixtures = ['users', 'sounds_with_tags']
    
    def setUp(self):
        self.user = User.objects.all()[0]
        self.sound = Sound.objects.all()[0] 

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
            'profile-wants_newsletter': True,
            'profile-enabled_stream_emails': True,
            'profile-about': 'About test text',
            'profile-signature': 'Signature test text',
            'profile-not_shown_in_online_users_list': True,
        })

        user = User.objects.select_related('profile').get(username="testuser")
        self.assertEqual(user.profile.home_page, 'http://www.example.com/')
        self.assertEqual(user.profile.wants_newsletter, True)
        self.assertEqual(user.profile.enabled_stream_emails, True)
        self.assertEqual(user.profile.about, 'About test text')
        self.assertEqual(user.profile.signature, 'Signature test text')
        self.assertEqual(user.profile.not_shown_in_online_users_list, True)

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
        self.assertEqual(user.pack_set.filter(name='Name of a new pack').exists(), True)
        self.assertEqual(Tag.objects.filter(name__contains="testtag").count(), 5)
        self.assertNotEqual(user.sounds.get(original_filename=filenames[0]).geotag, None)


class UserDelete(TestCase):

    fixtures = ['sounds']

    def create_user_and_content(self, is_index_dirty=True):
        user = User.objects.create_user("testuser", password="testpass")
        # Create comments
        target_sound = Sound.objects.all()[0]
        for i in range(0, 3):
            comment = Comment(comment="Comment %i" % i, user=user, content_object=target_sound)
            target_sound.add_comment(comment)
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


class DonationTest(TestCase):

    def test_donation_complete(self):
        params = {'txn_id': '8B703020T00352816',
                'payer_email': 'fs@freesound.org',
                'custom': 'Anonymous',
                'mc_currency': 'USD',
                'mc_gross': '1.00'}

        with mock.patch('accounts.views.requests') as mock_requests:
            mock_response = mock.Mock(text='VERIFIED')
            mock_requests.post.return_value = mock_response
            resp = self.client.post(reverse('donation-complete'), params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(accounts.models.Donation.objects.filter(\
                transaction_id='8B703020T00352816').exists(), True)

