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
import os
import time
from unittest import mock

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.cache.backends import locmem
from django.core.management import call_command
from django.http import HttpResponse
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

import accounts
from accounts.models import EmailPreferenceType
from comments.models import Comment
from general.templatetags.filter_img import replace_img
from geotags.models import GeoTag
from sounds.forms import PackForm
from sounds.models import Download, PackDownload, PackDownloadSound, SoundAnalysis, Pack, Sound, License, DeletedSound
from utils.cache import get_template_cache_key
from utils.test_helpers import create_user_and_sounds, override_analysis_path_with_temp_directory


class CommentSoundsTestCase(TestCase):

    fixtures = ['licenses', 'sounds', 'email_preference_type']

    def test_add_comment(self):
        sound = Sound.objects.get(id=19)
        user = User.objects.get(id=2)
        current_num_comments = sound.num_comments
        self.assertEqual(current_num_comments, sound.num_comments)
        sound.add_comment(user, "Test comment")
        sound.refresh_from_db()
        self.assertEqual(current_num_comments + 1, sound.num_comments)
        self.assertTrue(sound.is_index_dirty)

    def test_email_notification_on_send_email(self):
        # Add a comment to a sound using the view and test that email was sent
        sound = Sound.objects.get(id=19)
        commenting_user = User.objects.get(id=2)
        self.client.force_login(commenting_user)
        self.client.post(reverse('sound', args=[sound.user.username, sound.id]), {'comment': 'Test comment'})
        self.assertEqual(sound.comments.all().count(), 1)

        # Check email was sent notifying about comment
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(settings.EMAIL_SUBJECT_PREFIX in mail.outbox[0].subject)
        self.assertTrue(settings.EMAIL_SUBJECT_NEW_COMMENT in mail.outbox[0].subject)

        # Test that when the owner of a sound makes a comment, no email notification is sent
        self.client.force_login(sound.user)
        self.client.post(reverse('sound', args=[sound.user.username, sound.id]), {'comment': 'A comment by the owner'})
        self.assertEqual(sound.comments.all().count(), 2)
        self.assertEqual(len(mail.outbox), 1)

        # Now update preferences of sound.user to disable comment notification emails
        # We create an email preference object for the email type (which will mean user does not want new comment
        # emails as it is enabled by default and the preference indicates user does not want it).
        email_pref = accounts.models.EmailPreferenceType.objects.get(name="new_comment")
        accounts.models.UserEmailSetting.objects.create(user=sound.user, email_type=email_pref)

        # Make the comment again (from the commenting user) and assert no new email has been sent
        self.client.force_login(commenting_user)
        self.client.post(reverse('sound', args=[sound.user.username, sound.id]), {'comment': 'Another test comment'})
        self.assertEqual(sound.comments.all().count(), 3)
        self.assertEqual(len(mail.outbox), 1)

    def test_unsecure_content(self):
        comment = None
        self.assertEqual(replace_img(comment), None)

        comment = 'Test <img src="http://test.com/img.png" /> test'
        replaced_comment = 'Test <a href="http://test.com/img.png">http://test.com/img.png</a> test'
        self.assertEqual(replace_img(comment), replaced_comment)

        replaced_comment = 'Test <a href="http://test.com/img.png">http://test.com/img.png</a> test'
        comment = 'Test <img class="test" src="http://test.com/img.png" /> test'
        self.assertEqual(replace_img(comment), replaced_comment)

        comment = 'Test <img src="https://test.com/img.png" /> test'
        self.assertEqual(replace_img(comment), comment)

        # make sure lack of src doesn't break anything
        comment = 'Test <img/> test, http://test.com/img.png'
        self.assertEqual(replace_img(comment), comment)

    def test_post_delete_comment(self):
        sound = Sound.objects.get(id=19)
        sound.is_index_dirty = False
        sound.num_comments = 3
        sound.save()
        sound.post_delete_comment()
        sound.refresh_from_db()
        self.assertEqual(2, sound.num_comments)
        self.assertTrue(sound.is_index_dirty)

    def test_delete_comment(self):
        sound = Sound.objects.get(id=19)
        user = User.objects.get(id=2)
        current_num_comments = sound.num_comments
        sound.add_comment(user, "Test comment")
        comment = sound.comments.all()[0]
        comment.delete()
        sound = Sound.objects.get(id=19)
        self.assertEqual(current_num_comments, sound.num_comments)
        self.assertTrue(sound.is_index_dirty)


class ChangeSoundOwnerTestCase(TestCase):

    fixtures = ['licenses']

    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_change_sound_owner(self, delete_sounds_from_search_engine):
        # Prepare some content
        userA, packsA, soundsA = create_user_and_sounds(num_sounds=4, num_packs=1, tags="tag1 tag2 tag3 tag4 tag5")
        userB, _, _ = create_user_and_sounds(num_sounds=0, num_packs=0,
                                             user=User.objects.create_user("testuser2", password="testpass2"))

        fake_original_path_template = '/test/path/{sound_id}_{user_id}.wav'

        for sound in soundsA:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")
            sound.original_path = fake_original_path_template.format(sound_id=sound.id, user_id=userA.id)
            sound.save()

        # Check initial number of sounds is ok
        self.assertEqual(userA.profile.num_sounds, 4)
        self.assertEqual(userB.profile.num_sounds, 0)

        # Select change to change ownership and change index dirty for later checks
        target_sound = soundsA[0]
        target_sound.is_index_dirty = False
        target_sound.save()
        target_sound_id = target_sound.id
        target_sound_pack = target_sound.pack
        target_sound_tags = [ti.id for ti in target_sound.tags.all()]
        remaining_sound_ids = [s.id for s in soundsA[1:]]  # Other sounds that the user owns

        # Change ownership of sound
        target_sound.change_owner(userB)

        # Perform checks
        sound = Sound.objects.get(id=target_sound_id)
        self.assertEqual(userA.profile.num_sounds, 3)
        self.assertEqual(userB.profile.num_sounds, 1)
        self.assertEqual(sound.user, userB)
        self.assertTrue(sound.is_index_dirty)
        self.assertEqual(sound.pack.name, target_sound_pack.name)
        self.assertEqual(sound.pack.num_sounds, 1)
        self.assertEqual(target_sound_pack.num_sounds, 3)
        self.assertEqual(sound.pack.user, userB)
        self.assertEqual(sound.original_path, fake_original_path_template.format(sound_id=sound.id, user_id=userB.id))

        # Delete original user and perform further checks
        userA.profile.delete_user(delete_user_object_from_db=True)
        sound = Sound.objects.get(id=target_sound_id)
        self.assertCountEqual([ti.id for ti in sound.tags.all()], target_sound_tags)
        delete_sounds_from_search_engine.assert_has_calls([mock.call([i]) for i in remaining_sound_ids], any_order=True)


class ProfileNumSoundsTestCase(TestCase):

    fixtures = ['licenses']

    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_moderation_and_processing_state_changes(self, delete_sounds_from_search_engine):
        user, packs, sounds = create_user_and_sounds()
        sound = sounds[0]
        self.assertEqual(user.profile.num_sounds, 0)  # Sound not yet moderated or processed
        sound.change_moderation_state("OK")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound not yet processed
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound now processed and moderated
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound reprocessed and again set as ok
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound reprocessed second time and again set as ok
        sound.change_processing_state("FA")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound failed processing
        delete_sounds_from_search_engine.assert_called_once_with([sound.id])
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound processed again as ok
        sound.change_moderation_state("DE")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound unmoderated
        self.assertEqual(delete_sounds_from_search_engine.call_count, 2) # Sound deleted once when going to FA, once when DE

    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_sound_delete(self, delete_sounds_from_search_engine):
        user, packs, sounds = create_user_and_sounds()
        sound = sounds[0]
        sound_id = sound.id
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        sound.add_comment(user, "some comment")
        self.assertEqual(user.profile.num_sounds, 1)
        self.assertEqual(Comment.objects.count(), 1)
        sound.delete()
        self.assertEqual(user.profile.num_sounds, 0)
        self.assertEqual(Comment.objects.count(), 0)
        delete_sounds_from_search_engine.assert_called_once_with([sound_id])

    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_deletedsound_creation(self, delete_sounds_from_search_engine):
        user, packs, sounds = create_user_and_sounds()
        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        GeoTag.objects.create(sound=sound, lat=45.8498, lon=-62.6879, zoom=9)

        sound_id = sound.id
        sound.delete()
        delete_sounds_from_search_engine.assert_called_once_with([sound_id])

        self.assertEqual(DeletedSound.objects.filter(sound_id=sound_id).exists(), True)
        ds = DeletedSound.objects.get(sound_id=sound_id)

        # Check this elements are in the json saved on DeletedSound
        keys = ['num_ratings', 'duration', 'id', 'comments',
                'num_downloads', 'md5', 'description',
                'original_path', 'pack_id', 'license', 'created',
                'original_filename', 'geotag']

        json_data = list(ds.data.keys())
        for k in keys:
            self.assertTrue(k in json_data, f"{k} not in data")
        self.assertEqual(ds.data['geotag']['lat'], 45.8498)

    def test_pack_delete(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=5, num_packs=1)
        for sound in sounds:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")
        self.assertEqual(user.profile.num_sounds, 5)
        pack = packs[0]
        pack.delete_pack(remove_sounds=False)
        self.assertEqual(User.objects.get(id=user.id).profile.num_sounds, 5)  # Should be 5 as sounds are not deleted
        self.assertEqual(pack.is_deleted, True)




class SoundViewsTestCase(TestCase):

    fixtures = ['licenses']

    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_delete_sound(self, delete_sounds_from_search_engine):
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=1)
        sound = sounds[0]
        sound_id = sound.id
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        self.client.force_login(user)
        _, _, sounds_other_user = create_user_and_sounds(num_sounds=1, username="testuser4")

        # Try to delete a sound not owned by the request user (should return 200 but not delete the sound)
        resp = self.client.post(reverse('accounts-manage-sounds', args=['published']),
            {"delete_confirm": "delete_confirm", "object-ids": [sounds_other_user[0].id]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Sound.objects.filter(id=sounds_other_user[0].id).count(), 1)

        # Try to delete a sound owned the user (should delete sound)
        resp = self.client.post(reverse('accounts-manage-sounds', args=['published']),
            {"delete_confirm": "delete_confirm", "object-ids": [sound.id]}, follow=True)
        self.assertEqual(Sound.objects.filter(id=sound_id).count(), 0)
        self.assertEqual(resp.status_code, 200)
        delete_sounds_from_search_engine.assert_called_once_with([sound.id])

    def test_embed_iframe(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=1)
        sound = sounds[0]
        sound.moderation_state = 'OK'
        sound.processing_state = 'OK'
        sound.save()
        resp = self.client.get(reverse('embed-simple-sound-iframe',
            kwargs={"sound_id": sound.id, 'player_size': 'medium'}))
        self.assertEqual(resp.status_code, 200)

    def test_sound_short_link(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=1)
        sound = sounds[0]
        resp = self.client.get(reverse('short-sound-link', kwargs={"sound_id": sound.id}))
        self.assertEqual(resp.status_code, 302)

    def test_oembed_sound(self):
        # Get iframe of a sound using oembed
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=1)
        sound = sounds[0]
        sound_id = sound.id
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        self.client.force_login(user)

        # Get url of the sound
        url = reverse('sound', args=[sound.user.username, sound_id])

        resp = self.client.get(reverse('oembed-sound')+'?url='+url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content != '')

    def test_oldusername_sound_redirect(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=1)
        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")

        # Add new OldUsername to the user
        accounts.models.OldUsername.objects.create(user=sound.user, username='oldusername')

        # get url of the sound with oldusername
        url = reverse('sound', args=['oldusername', sound.id])
        resp = self.client.get(url)

        url = reverse('sound', args=[sound.user.username, sound.id])
        # Check redirect to new username
        self.assertRedirects(resp, url, status_code=301)

        # Check using wrong username
        url = reverse('sound', args=['wrongusername', sound.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


class SoundPackDownloadTestCase(TestCase):

    fixtures = ['licenses']

    def setUp(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=1)
        self.sound = sounds[0]
        self.sound.moderation_state = "OK"
        self.sound.processing_state = "OK"
        self.sound.save()
        self.pack = packs[0]
        self.user = user
        self.factory = RequestFactory()

    def test_download_sound(self):
        with mock.patch('sounds.views.sendfile', return_value=HttpResponse()):

            # Check sound can't be downloaded if user not logged in
            resp = self.client.get(reverse('sound-download', args=[self.sound.user.username, self.sound.id]))
            self.assertRedirects(resp, '{}?next={}'.format(
            reverse('login'), reverse('sound', args=[self.sound.user.username, self.sound.id])))

            # Check download works successfully if user logged in
            self.client.force_login(self.user)
            resp = self.client.get(reverse('sound-download', args=[self.sound.user.username, self.sound.id]))
            self.assertEqual(resp.status_code, 200)

            # Check n download objects is 1
            self.assertEqual(Download.objects.filter(user=self.user, sound=self.sound).count(), 1)

            # Download again and check n download objects is still 1
            self.client.get(reverse('sound-download', args=[self.sound.user.username, self.sound.id]))
            self.assertEqual(Download.objects.filter(user=self.user, sound=self.sound).count(), 1)

            # Check num_download attribute of Sound is 1
            self.sound.refresh_from_db()
            self.assertEqual(self.sound.num_downloads, 1)

            # Check num_sound_downloads in user profile has been updated
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_sound_downloads, 1)

            # Delete all Download objects and check num_download attribute of Sound is 0
            Download.objects.all().delete()
            self.sound.refresh_from_db()
            self.assertEqual(self.sound.num_downloads, 0)

            # Check num_sound_downloads in user profile has been updated
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_sound_downloads, 0)

    def test_download_sound_oldusername(self):
        # Test if download works if username changed
        with mock.patch('sounds.views.sendfile', return_value=HttpResponse()):

            self.sound.user.username = 'other_username'
            self.sound.user.save()

            # Check download works successfully if user logged in
            self.client.force_login(self.user)
            resp = self.client.get(reverse('sound-download', args=['testuser', self.sound.id]))
            # Check if response is 301
            self.assertEqual(resp.status_code, 301)

            # Now follow redirect
            resp = self.client.get(reverse('sound-download', args=['testuser', self.sound.id]), follow=True)
            self.assertEqual(resp.status_code, 200)

            # Check n download objects is 1
            self.assertEqual(Download.objects.filter(user=self.user, sound=self.sound).count(), 1)

    def test_download_pack(self):
        with mock.patch('sounds.views.download_sounds', return_value=HttpResponse()):

            # Check sound can't be downloaded if user not logged in
            resp = self.client.get(reverse('pack-download', args=[self.sound.user.username, self.pack.id]))
            self.assertRedirects(resp, '{}?next={}'.format(
            reverse('login'), reverse('pack', args=[self.sound.user.username, self.pack.id])))

            # Check download works successfully if user logged in
            self.client.force_login(self.user)
            resp = self.client.get(reverse('pack-download', args=[self.sound.user.username, self.pack.id]))
            self.assertEqual(resp.status_code, 200)

            # Check n download objects is 1
            self.assertEqual(PackDownload.objects.filter(user=self.user, pack=self.pack).count(), 1)

            # Check the number of PackDownloadSounds
            self.assertEqual(PackDownloadSound.objects.filter(
                pack_download__user=self.user, pack_download__pack=self.pack).count(), 1)

            # Download again and check n download objects is still 1
            self.client.get(reverse('pack-download', args=[self.sound.user.username, self.pack.id]))
            self.assertEqual(PackDownload.objects.filter(user=self.user, pack=self.pack).count(), 1)

            # Check num_download attribute of Sound is 1
            self.pack.refresh_from_db()
            self.assertEqual(self.pack.num_downloads, 1)

            # Check num_pack_downloads in user profile has been updated
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_pack_downloads, 1)

            # Delete all Download objects and check num_download attribute of Sound is 0
            PackDownload.objects.all().delete()
            self.pack.refresh_from_db()
            self.assertEqual(self.pack.num_downloads, 0)

            # Check num_pack_downloads in user profile has been updated
            self.user.profile.refresh_from_db()
            self.assertEqual(self.user.profile.num_pack_downloads, 0)

    def test_download_pack_oldusername(self):
        # Test if download pack works if username changed
        with mock.patch('sounds.views.sendfile', return_value=HttpResponse()):

            self.pack.user.username = 'other_username'
            self.pack.user.save()

            # Check download works successfully if user logged in
            self.client.force_login(self.user)

            # First check that the response is a 301
            resp = self.client.get(reverse('pack-download', args=['testuser', self.pack.id]))
            self.assertEqual(resp.status_code, 301)

            # Now follow the redirect
            resp = self.client.get(reverse('pack-download', args=['testuser', self.pack.id]), follow=True)
            self.assertEqual(resp.status_code, 200)

            # Check n download objects is 1
            self.assertEqual(PackDownload.objects.filter(user=self.user, pack=self.pack).count(), 1)


class SoundSignatureTestCase(TestCase):

    fixtures = ['licenses', 'user_groups']

    def setUp(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=1)
        self.SOUND_DESCRIPTION = 'Simple Sound Description'
        self.USER_SOUND_SIGNATURE = 'Sound Signature.'
        self.USER_VISITOR_SOUND_SIGNATURE = 'Sound Visitor Signature.'
        self.sound = sounds[0]
        self.sound.description = self.SOUND_DESCRIPTION
        self.sound.moderation_state = "OK"
        self.sound.processing_state = "OK"
        self.sound.save()
        self.user = user
        self.user_visitor = User.objects.create_user(
            username='testuservisitor', password='testpassword')

    def test_no_signature(self):
        """Check signature is not present in sound page (regardless of the user who visits and the authentication)"""

        # Non-logged in user
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertNotContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)

        # Logged-in user (creator of the sound)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertNotContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)

        # Logged-in user (non-creator of the sound)
        self.client.force_login(self.user_visitor)
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertNotContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)

        # Set a signature to the visitor user, check that his signature does not appear in the sound
        self.user_visitor.profile.sound_signature = self.USER_VISITOR_SOUND_SIGNATURE
        self.user_visitor.profile.save()
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertNotContains(resp, self.USER_VISITOR_SOUND_SIGNATURE, status_code=200, html=True)

    def test_signature(self):
        """Check signature is present in the sound page (regardless of the user who visits and the authentication)"""

        self.user.profile.sound_signature = self.USER_SOUND_SIGNATURE
        self.user.profile.save()

        # Non-logged in user
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)

        # Logged-in user (creator of the sound)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)

        # Logged-in user (non-creator of the sound)
        self.client.force_login(self.user_visitor)
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)


class SoundTemplateCacheTests(TestCase):
    fixtures = ['licenses', 'email_preference_type']

    def setUp(self):
        cache.clear()
        user, packs, sounds = create_user_and_sounds(num_sounds=1, tags="tag1 tag2 tag3", description="Test description")
        self.sound = sounds[0]
        self.sound.change_processing_state("OK")
        self.sound.change_moderation_state("OK")
        self.user = user

    def _get_sound_view_cache_keys(self):
        return ([get_template_cache_key('bw_sound_page', self.sound.id),
                 get_template_cache_key('bw_sound_page_sidebar', self.sound.id)])

    def _get_sound_view_footer_top_cache_keys(self):
        return [get_template_cache_key('bw_sound_page', self.sound.id)]

    def _get_sound_display_cache_keys(self, is_authenticated=True, is_explicit=False, player_size='small'):
        return [get_template_cache_key('bw_display_sound', self.sound.id, player_size, is_authenticated)]

    def _assertCacheAbsent(self, cache_keys):
        for cache_key in cache_keys:
            self.assertIsNone(cache.get(cache_key))

    def _assertCachePresent(self, cache_keys):
        for cache_key in cache_keys:
            self.assertIsNotNone(cache.get(cache_key))

    def _get_sound_url(self, viewname, username=None, sound_id=None):
        return reverse(viewname, args=[username or self.sound.user.username, sound_id or self.sound.id])

    def _get_sound_view(self):
        return self.client.get(self._get_sound_url('sound'))

    def _get_sound_from_profile_page(self, user):
        return self.client.get(reverse('account', args=[user.username]))

    def _print_cache(self, cache_keys):
        print(list(locmem._caches[''].keys()))
        print(cache_keys)

    def test_update_description(self):

        cache_keys = self._get_sound_view_cache_keys()
        self._assertCacheAbsent(cache_keys)

        # Test as an authenticated user, although it doesn't matter in this case because cache templates are the same
        # for both logged in and anonymous user.
        self.client.force_login(self.user)

        resp = self._get_sound_view()
        self.assertEqual(resp.status_code, 200)
        self._assertCachePresent(cache_keys)

        # Edit sound
        new_description = 'New description'
        new_name = 'New name'
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': new_description,
            '0-name': new_name,
            '0-tags': 'tag1 tag2 tag3',
            '0-license': ['3'],
        })
        self.assertEqual(resp.status_code, 302)

        # Check that keys are no longer in cache
        self._assertCacheAbsent(cache_keys)

        # Check that the information is updated properly
        resp = self._get_sound_view()
        self.assertContains(resp, new_description, html=True)
        self.assertContains(resp, new_name, html=True)

    def _get_delete_comment_url(self, html):
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find('a', {'title': 'Delete comment'})
        return tag['data-modal-confirmation-url']

    # Comments are only cached in display
    def test_add_remove_comment(self):
        cache_keys = self._get_sound_display_cache_keys()
        self._assertCacheAbsent(cache_keys)
        self.client.force_login(self.user)

        # Check the initial state (0 comments)
        resp = self._get_sound_from_profile_page(self.user)
        self.assertContains(resp, 'data-num-comments="0"')
        self._assertCachePresent(cache_keys)

        # Add comment
        resp = self.client.post(self._get_sound_url('sound'), {
            'comment': 'Test comment'
        }, follow=True)  # we are testing sound-display, rendering sound view is ok
        delete_url = self._get_delete_comment_url(resp.content)
        self._assertCacheAbsent(cache_keys)

        # Verify that sound display has updated number of comments
        resp = self._get_sound_from_profile_page(self.user)
        self.assertContains(resp, 'data-num-comments="1"')
        self._assertCachePresent(cache_keys)

        # Delete the comment
        resp = self.client.get(delete_url)
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Verify that sound display has no comments
        resp = self._get_sound_from_profile_page(self.user)
        self.assertContains(resp, 'data-num-comments="0"')

    # Downloads are only cached in display
    @mock.patch('sounds.views.sendfile', return_value=HttpResponse('Dummy response'))
    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    def test_download(self, sendfile):
        cache_keys = self._get_sound_display_cache_keys()
        self._assertCacheAbsent(cache_keys)

        self.client.force_login(self.user)

        resp = self._get_sound_from_profile_page(self.user)
        self.assertContains(resp, 'data-num-downloads="0"')
        self._assertCachePresent(cache_keys)

        # Download
        resp = self.client.get(self._get_sound_url('sound-download'))
        sendfile.assert_called_once_with(self.sound.locations("path"),
                                         self.sound.friendly_filename(),
                                         self.sound.locations("sendfile_url"))
        self.assertEqual(resp.status_code, 200)
        self._assertCacheAbsent(cache_keys)

        # Verify that sound display has updated number of downloads
        resp = self._get_sound_from_profile_page(self.user)
        self.assertContains(resp, 'data-num-downloads="1"')

    # Similarity link (cached in display and view)
    @mock.patch('general.management.commands.similarity_update.Similarity.add', return_value='Dummy response')
    def _test_similarity_update(self, cache_keys, expected, request_func, similarity_add, user=None):
        # Create a SoundAnalysis object with status OK so "similarity_update" command will pick it up
        SoundAnalysis.objects.create(sound=self.sound, analyzer=settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME, analysis_status="OK")
        self.sound.save()

        self._assertCacheAbsent(cache_keys)

        self.client.force_login(self.user)

        # Initial check
        self.assertEqual(self.sound.similarity_state, 'PE')
        self.assertNotContains(request_func(user) if user is not None else request_func(), expected)
        self._assertCachePresent(cache_keys)

        # Update similarity
        call_command('similarity_update')
        similarity_add.assert_called_once_with(self.sound.id, self.sound.locations('analysis.statistics.path'))
        self._assertCacheAbsent(cache_keys)

        # Check similarity icon
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.similarity_state, 'OK')
        self.assertContains(request_func(user) if user is not None else request_func(), expected)


    # Pack link (cached in display and view)
    def _test_add_remove_pack(self, cache_keys, text, request_func, user=None):
        self._assertCacheAbsent(cache_keys)

        self.client.force_login(self.user)

        self.assertIsNone(self.sound.pack)
        self.assertNotContains(request_func(user) if user is not None else request_func(), text)
        self._assertCachePresent(cache_keys)

        # Add sound to pack
        pack_name = 'New pack'
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': self.sound.description,
            '0-name': self.sound.original_filename,
            '0-tags': self.sound.get_sound_tags_string(),
            '0-license': self.sound.license_id,
            '0-new_pack': pack_name,
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check pack icon
        self.sound.refresh_from_db()
        self.assertIsNotNone(self.sound.pack)
        self.assertContains(request_func(user) if user is not None else request_func(), text)  # request_func should render the template
        self._assertCachePresent(cache_keys)

        # Remove sound from pack
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': self.sound.description,
            '0-name': self.sound.original_filename,
            '0-tags': self.sound.get_sound_tags_string(),
            '0-license': self.sound.license_id,
            '0-pack': '',
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check pack icon being absent
        self.sound.refresh_from_db()
        self.assertIsNone(self.sound.pack)
        self.assertNotContains(request_func(user) if user is not None else request_func(), text)

    def test_add_remove_pack_display(self):
        self._test_add_remove_pack(
            self._get_sound_display_cache_keys(),
            'class="bw-icon-stack"',
            self._get_sound_from_profile_page,
            user=self.user,
        )

    def test_add_remove_pack_view(self):
        self._test_add_remove_pack(
            self._get_sound_view_footer_top_cache_keys(),
            'This sound is part of the pack',
            self._get_sound_view,
        )

    # Geotag link (cached in display and view)
    def _test_add_remove_geotag(self, cache_keys, text, request_func, user=None):
        self._assertCacheAbsent(cache_keys)

        self.client.force_login(self.user)

        with self.assertRaises(GeoTag.DoesNotExist):
            assert self.sound.geotag
        self.assertNotContains(request_func(user) if user is not None else request_func() if user is not None else request_func(), text)
        self._assertCachePresent(cache_keys)

        # Add a geotag to the sound
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': self.sound.description,
            '0-name': self.sound.original_filename,
            '0-tags': self.sound.get_sound_tags_string(),
            '0-license': self.sound.license_id,
            '0-lat': 20,
            '0-lon': 20,
            '0-zoom': 18
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check geotag icon
        self.sound.refresh_from_db()
        self.assertIsNotNone(self.sound.geotag)
        self.assertContains(request_func(user) if user is not None else request_func(), text)
        self._assertCachePresent(cache_keys)

        # Remove geotag from the sound
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': self.sound.description,
            '0-name': self.sound.original_filename,
            '0-tags': self.sound.get_sound_tags_string(),
            '0-license': self.sound.license_id,
            '0-remove_geotag': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check geotag icon being absent
        self.sound.refresh_from_db()
        with self.assertRaises(GeoTag.DoesNotExist):
            assert self.sound.geotag
        self.assertNotContains(request_func(user) if user is not None else request_func(), text)

    def test_add_remove_geotag_display(self):
        self._test_add_remove_geotag(
            self._get_sound_display_cache_keys(),
            'class="bw-icon-pin',
            self._get_sound_from_profile_page,
            user=self.user,
        )

    def test_add_remove_geotag_view(self):
        self._test_add_remove_geotag(
            self._get_sound_view_footer_top_cache_keys(),
            'class="bw-icon-pin',
            self._get_sound_view,
        )

    # Changing license
    def _test_change_license(self, cache_keys, new_license, expected_text, request_func, user=None):
        self._assertCacheAbsent(cache_keys)

        self.client.force_login(self.user)

        self.assertNotEqual(self.sound.license, new_license)
        self.assertNotContains(request_func(user) if user is not None else request_func(), expected_text)
        self._assertCachePresent(cache_keys)

        # Change license
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': self.sound.description,
            '0-name': self.sound.original_filename,
            '0-tags': self.sound.get_sound_tags_string(),
            '0-license': new_license.id,
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check that license is updated
        self.assertContains(request_func(user) if user is not None else request_func(), expected_text)

    def test_change_license_display(self):
        self._test_change_license(
            self._get_sound_display_cache_keys(),
            License.objects.filter(name__iexact='Creative Commons 0').last(),
            "bw-icon-zero",
            self._get_sound_from_profile_page,
            user=self.user,
        )

    def test_change_license_view(self):
        license = License.objects.filter(name__iexact='Creative Commons 0').first()
        self._test_change_license(
            self._get_sound_view_footer_top_cache_keys(),
            license,
            str(license.name_with_version),
            self._get_sound_view,
        )

    def _test_add_remove_remixes(self, cache_keys, text, request_func, user=None):
        _, _, sounds = create_user_and_sounds(num_sounds=1, user=self.user)
        another_sound = sounds[0]
        self._assertCacheAbsent(cache_keys)

        self.client.force_login(self.user)

        self.assertEqual(self.sound.remix_group.count(), 0)
        self.assertNotContains(request_func(user) if user is not None else request_func(), text)
        self._assertCachePresent(cache_keys)

        # Indicate another sound as source
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': self.sound.description,
            '0-name': self.sound.original_filename,
            '0-tags': self.sound.get_sound_tags_string(),
            '0-license': self.sound.license_id,
            '0-sources': str(another_sound.id)
        })
        self.assertEqual(resp.status_code, 302)
        call_command('create_remix_groups')
        self._assertCacheAbsent(cache_keys)

        # Check remix icon
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.remix_group.count(), 1)
        self.assertContains(request_func(user) if user is not None else request_func(), text)
        self._assertCachePresent(cache_keys)

        # Remove remix from the sound
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            '0-sound_id': self.sound.id,
            '0-bst_category': 'ss-n',
            '0-description': self.sound.description,
            '0-name': self.sound.original_filename,
            '0-tags': self.sound.get_sound_tags_string(),
            '0-license': self.sound.license_id,
            '0-sources': ''
        })
        self.assertEqual(resp.status_code, 302)
        call_command('create_remix_groups')
        self._assertCacheAbsent(cache_keys)

        # Check remix icon being absent
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.remix_group.count(), 0)
        self.assertNotContains(request_func(user) if user is not None else request_func(), text)

    def test_add_remove_remixes_display(self):
        self._test_add_remove_remixes(
            self._get_sound_display_cache_keys(),
            'data-remix-group="true"',
            self._get_sound_from_profile_page,
            user=self.user,
        )

    def test_add_remove_remixes_view(self):
        self._test_add_remove_remixes(
            self._get_sound_view_footer_top_cache_keys(),
            'class="bw-icon-remix',
            self._get_sound_view
        )

    def _test_state_change(self, cache_keys, change_state, texts):
        """@:param check_present - function that checks presence of indication of not 'OK' state"""
        self.client.force_login(self.user)

        self._assertCacheAbsent(cache_keys)
        resp = self.client.get(self._get_sound_url('sound'))
        for text in texts:
            self.assertContains(resp, text)
        self._assertCachePresent(cache_keys)

        # Change processing state
        change_state()

        self._assertCacheAbsent(cache_keys)
        resp = self.client.get(self._get_sound_url('sound'))
        for text in texts:
            self.assertNotContains(resp, text)
        self._assertCachePresent(cache_keys)

    def test_processing_state_change_view(self):
        self.sound.change_processing_state('PE')
        self._test_state_change(
            self._get_sound_view_cache_keys(),
            lambda: self.sound.change_processing_state('OK'),
            ['sound not yet processed or moderated'],
        )

    def test_moderation_state_change_view(self):
        self.sound.change_moderation_state('PE')
        self._test_state_change(
            self._get_sound_view_cache_keys(),
            lambda: self.sound.change_moderation_state('OK'),
            ['sound not yet processed or moderated'],
        )


class SoundAnalysisModel(TestCase):

    fixtures = ['licenses']

    @override_analysis_path_with_temp_directory
    def test_get_analysis(self):
        _, _, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]
        analysis_data = {
            'feature_float': 1.0,
            'feature_int': 1,
            'feature_string': 'string',
            'feature_list_string': ['a', 'b', 'c'],
            'feature_bool': True,
            'feature_array_float': [0.1, 0.2, 0.3],
            'feature_json': {'a': 1, 'b': 2}
        }

        # Create one analysis object that stores the data in the model. Check that get_analysis returns correct data.
        sa = SoundAnalysis.objects.create(sound=sound, analyzer="TestExtractor1", analysis_data=analysis_data,
                                          analysis_status="OK")
        self.assertEqual(sound.analyses.all().count(), 1)
        self.assertEqual(list(sa.get_analysis_data().keys()), list(analysis_data.keys()))
        self.assertEqual(sa.get_analysis_data()['feature_float'], 1.0)
        self.assertEqual(sa.get_analysis_data()['feature_int'], 1)
        self.assertEqual(sa.get_analysis_data()['feature_string'], 'string')
        self.assertEqual(sa.get_analysis_data()['feature_list_string'], ['a', 'b', 'c'])
        self.assertEqual(sa.get_analysis_data()['feature_bool'], True)
        self.assertEqual(sa.get_analysis_data()['feature_array_float'], [0.1, 0.2, 0.3])
        self.assertEqual(sa.get_analysis_data()['feature_json'], {'a': 1, 'b': 2})

        # Now create an analysis object which stores output in a JSON file. Again check that get_analysis works.
        analysis_filename = '%i-TestExtractor2.json' % sound.id
        sound_analysis_folder = os.path.join(settings.ANALYSIS_PATH, str(sound.id // 1000))
        os.makedirs(sound_analysis_folder, exist_ok=True)
        with open(os.path.join(sound_analysis_folder, analysis_filename), 'w') as f:
            json.dump(analysis_data, f)
        sa2 = SoundAnalysis.objects.create(sound=sound, analyzer="TestExtractor2", analysis_status="OK")
        self.assertEqual(sound.analyses.all().count(), 2)
        self.assertEqual(list(sa2.get_analysis_data().keys()), list(analysis_data.keys()))
        self.assertEqual(sa2.get_analysis_data()['feature_float'], 1.0)
        self.assertEqual(sa2.get_analysis_data()['feature_int'], 1)
        self.assertEqual(sa2.get_analysis_data()['feature_string'], 'string')
        self.assertEqual(sa2.get_analysis_data()['feature_list_string'], ['a', 'b', 'c'])
        self.assertEqual(sa2.get_analysis_data()['feature_bool'], True)
        self.assertEqual(sa2.get_analysis_data()['feature_array_float'], [0.1, 0.2, 0.3])
        self.assertEqual(sa2.get_analysis_data()['feature_json'], {'a': 1, 'b': 2})

        # Create an analysis object which references a non-existing file. Check that get_analysis returns None.
        sa3 = SoundAnalysis.objects.create(sound=sound, analyzer="TestExtractor3", analysis_status="OK")
        self.assertEqual(sound.analyses.all().count(), 3)
        self.assertEqual(sa3.get_analysis_data(), {})


class SoundEditDeletePermissionTestCase(TestCase):
    """Test that when editing and deleting sounds and packs only the user who owns
    them, or a specific admin can make the change"""

    fixtures = ['licenses', 'sounds']

    def setUp(self):
        # From sounds.json fixture
        self.sound = Sound.objects.get(pk=6)
        self.pack = Pack.objects.get(pk=5103)
        self.sound_user = User.objects.get(username=self.sound.user.username)
        self.other_user = User.objects.get(username='Anton')
        self.admin_user = User.objects.get(username='Bram')

    def test_edit_sound_owner(self):
        # Sound owner
        self.client.force_login(self.sound_user)
        resp = self.client.get(reverse('sound-edit', args=[self.sound.user.username, self.sound.id]))
        self.assertEqual(resp.status_code, 200)

        # Admin
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse('sound-edit', args=[self.sound.user.username, self.sound.id]))
        self.assertEqual(resp.status_code, 200)

        # Other user
        self.client.force_login(self.other_user)
        resp = self.client.post(reverse('sound-edit', args=[self.sound.user.username, self.sound.id]))
        self.assertEqual(resp.status_code, 403)

    def test_edit_pack_owner(self):
        # Pack owner
        self.client.force_login(self.sound_user)
        resp = self.client.get(reverse('pack-edit', args=[self.pack.user.username, self.pack.id]))
        self.assertEqual(resp.status_code, 200)

        # Admin
        self.client.force_login(self.admin_user)
        resp = self.client.get(reverse('pack-edit', args=[self.pack.user.username, self.pack.id]))
        self.assertEqual(resp.status_code, 200)

        # Other user
        self.client.force_login(self.other_user)
        resp = self.client.post(reverse('pack-edit', args=[self.pack.user.username, self.pack.id]))
        self.assertEqual(resp.status_code, 403)



class SoundEditTestCase(TestCase):
    fixtures = ['licenses', 'email_preference_type']

    def setUp(self):
        cache.clear()
        user, _, sounds = create_user_and_sounds(num_sounds=3)
        self.sound = sounds[0]
        self.sound.change_processing_state("OK")
        self.sound.change_moderation_state("OK")
        self.user = user

    def test_update_description(self):

        self.client.force_login(self.user)
        new_description = 'New description'
        new_name = 'New name'
        new_tags = ['tag1', 'tag2', 'tag3']
        new_pack_name = 'Name of a new pack'
        new_bst_category = 'ss-n'
        new_sound_sources = Sound.objects.exclude(id=self.sound.id)
        geotag_lat = 46.31658418182218
        resp = self.client.post(reverse('sound-edit', args=[self.sound.user.username, self.sound.id]), {
            '0-sound_id': self.sound.id,
            '0-description': new_description,
            '0-name': new_name,
            '0-tags': ' '.join(new_tags),
            '0-license': '3',
            '0-sources': ','.join([f'{s.id}' for s in new_sound_sources]),
            '0-pack': PackForm.NEW_PACK_CHOICE_VALUE,
            '0-new_pack': new_pack_name,
            '0-bst_category': new_bst_category,
            '0-lat': f'{geotag_lat}',
            '0-lon': '3.515625',
            '0-zoom': '16',
        })
        self.assertEqual(resp.status_code, 302)

        self.sound.refresh_from_db()
        self.assertEqual(self.sound.description, new_description)
        self.assertEqual(self.sound.original_filename, new_name)
        self.assertEqual(self.sound.bst_category, new_bst_category)
        self.assertListEqual(sorted(self.sound.get_sound_tags()), sorted(new_tags))
        self.assertEqual(self.sound.sources.all().count(), len(new_sound_sources))
        self.assertTrue(Pack.objects.filter(name='Name of a new pack').exists())
        self.assertEqual(self.sound.pack.name, new_pack_name)
        self.assertIsNotNone(self.sound.geotag)
        self.assertAlmostEqual(self.sound.geotag.lat, geotag_lat)
