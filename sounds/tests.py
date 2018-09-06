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
import json
import tempfile
import time
import os
from itertools import count

import mock
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.core import mail
from django.core.cache import cache
from django.core.cache.backends import locmem
from django.core.management import call_command
from django.http import HttpRequest, HttpResponse
from django.template import Context, Template
from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse
from freezegun import freeze_time

import accounts
from comments.models import Comment
from general.templatetags.filter_img import replace_img
from sounds.models import Pack, Sound, SoundOfTheDay, License, DeletedSound, Flag
from sounds.models import Download, PackDownload, PackDownloadSound, SoundAnalysis
from sounds.views import get_sound_of_the_day_id
from accounts.models import EmailPreferenceType
from utils.encryption import encrypt
from utils.tags import clean_and_split_tags
from utils.cache import get_template_cache_key

from bs4 import BeautifulSoup


class OldSoundLinksRedirectTestCase(TestCase):

    fixtures = ['sounds']

    def setUp(self):
        self.sound = Sound.objects.all()[0]

    def test_old_sound_link_redirect_ok(self):
        # 301 permanent redirect, result exists
        response = self.client.get(reverse('old-sound-page'), data={'id': self.sound.id})
        self.assertEqual(response.status_code, 301)

    def test_old_sound_link_redirect_not_exists_id(self):
        # 404 id does not exist
        response = self.client.get(reverse('old-sound-page'), data={'id': 0}, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_old_sound_link_redirect_invalid_id(self):
        # 404 invalid id
        response = self.client.get(reverse('old-sound-page'), data={'id': 'invalid_id'}, follow=True)
        self.assertEqual(response.status_code, 404)


class OldPackLinksRedirectTestCase(TestCase):

    fixtures = ['packs']

    def setUp(self):
        self.client = Client()
        self.pack = Pack.objects.all()[0]

    def test_old_pack_link_redirect_ok(self):
        response = self.client.get(reverse('old-pack-page'), data={'id': self.pack.id})
        self.assertEqual(response.status_code, 301)

    def test_old_pack_link_redirect_not_exists_id(self):
        response = self.client.get(reverse('old-pack-page'), data={'id': 0}, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_old_pack_link_redirect_invalid_id(self):
        response = self.client.get(reverse('old-pack-page'), data={'id': 'invalid_id'}, follow=True)
        self.assertEqual(response.status_code, 404)


class RandomSoundAndUploaderTestCase(TestCase):

    fixtures = ['sounds']

    def test_random_sound(self):
        sound_obj = Sound.objects.random()
        self.assertEqual(isinstance(sound_obj, Sound), True)


class RandomSoundViewTestCase(TestCase):

    fixtures = ['initial_data']

    @mock.patch('sounds.views.get_random_sound_from_solr')
    def test_random_sound_view(self, random_sound):
        """ Get a sound from solr and redirect to it. """
        users, packs, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]

        # We only use the ID field from solr
        random_sound.return_value = {'id': sound.id}

        response = self.client.get(reverse('sounds-random'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/people/testuser/sounds/{}/?random_browsing=true'.format(sound.id))

    @mock.patch('sounds.views.get_random_sound_from_solr')
    def test_random_sound_view_bad_solr(self, random_sound):
        """ Solr may send us a sound id which no longer exists (index hasn't been updated).
        In this case, use the database access """
        users, packs, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]
        # Update sound attributes to be selected by Sound.objects.random
        sound.moderation_state = sound.processing_state = 'OK'
        sound.is_explicit = False
        sound.avg_rating = 8
        sound.num_ratings = 5
        sound.save()

        # We only use the ID field from solr
        random_sound.return_value = {'id': sound.id+100}

        # Even though solr returns sound.id+100, we find we are redirected to the db sound, because
        # we call Sound.objects.random
        response = self.client.get(reverse('sounds-random'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/people/testuser/sounds/{}/?random_browsing=true'.format(sound.id))

    @mock.patch('sounds.views.get_random_sound_from_solr')
    def test_random_sound_view_no_solr(self, random_sound):
        """ If solr is down, get a random sound from the database and redirect to it. """
        users, packs, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]
        # Update sound attributes to be selected by Sound.objects.random
        sound.moderation_state = sound.processing_state = 'OK'
        sound.is_explicit = False
        sound.avg_rating = 8
        sound.num_ratings = 5
        sound.save()

        # Returned if there is an issue accessing solr
        random_sound.return_value = {}

        # we find the sound due to Sound.objects.random
        response = self.client.get(reverse('sounds-random'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/people/testuser/sounds/{}/?random_browsing=true'.format(sound.id))


class CommentSoundsTestCase(TestCase):

    fixtures = ['sounds', 'email_preference_type']

    def test_add_comment(self):
        sound = Sound.objects.get(id=19)
        user = User.objects.get(id=2)
        current_num_comments = sound.num_comments
        self.assertEqual(current_num_comments, sound.num_comments)
        sound.add_comment(user, "Test comment")
        sound.refresh_from_db()
        self.assertEqual(current_num_comments + 1, sound.num_comments)
        self.assertEqual(sound.is_index_dirty, True)

    def test_email_notificaiton_on_send_email(self):
        # Add a comment to a sound using the view and test that email was sent
        sound = Sound.objects.get(id=19)
        commenting_user = User.objects.get(id=2)
        self.client.force_login(commenting_user)
        self.client.post(reverse('sound', args=[sound.user.username, sound.id]), {'comment': u'Test comment'})

        # Check email was sent notifying about comment
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, u'[freesound] You have a new comment.')

        # Now update preferences of sound.user to disable comment notification emails
        sound.user.profile.update_enabled_email_types([])  # Will set all to disabled if none is passed

        # Make the comment again and assert no new email has been sent
        self.client.post(reverse('sound', args=[sound.user.username, sound.id]), {'comment': u'Test comment'})
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
        self.assertEqual(sound.is_index_dirty, True)

    def test_delete_comment(self):
        sound = Sound.objects.get(id=19)
        user = User.objects.get(id=2)
        current_num_comments = sound.num_comments
        sound.add_comment(user, "Test comment")
        comment = sound.comments.all()[0]
        comment.delete()
        sound = Sound.objects.get(id=19)
        self.assertEqual(current_num_comments, sound.num_comments)
        self.assertEqual(sound.is_index_dirty, True)


sound_counter = count()


def create_user_and_sounds(num_sounds=1, num_packs=0, user=None, count_offset=0, tags=None):
    count_offset = count_offset + next(sound_counter)
    if user is None:
        user = User.objects.create_user("testuser", password="testpass", email='email@freesound.org')
    packs = list()
    for i in range(0, num_packs):
        pack = Pack.objects.create(user=user, name="Test pack %i" % (i + count_offset))
        packs.append(pack)
    sounds = list()
    for i in range(0, num_sounds):
        pack = None
        if packs:
            pack = packs[i % len(packs)]
        sound = Sound.objects.create(user=user,
                                     original_filename="Test sound %i" % (i + count_offset),
                                     base_filename_slug="test_sound_%i" % (i + count_offset),
                                     license=License.objects.all()[0],
                                     pack=pack,
                                     md5="fakemd5_%i" % (i + count_offset))
        if tags is not None:
            sound.set_tags(clean_and_split_tags(tags))
        sounds.append(sound)
    return user, packs, sounds


class ChangeSoundOwnerTestCase(TestCase):

    fixtures = ['initial_data']

    @mock.patch('sounds.models.delete_sound_from_solr')
    def test_change_sound_owner(self, delete_sound_solr):
        # Prepare some content
        userA, packsA, soundsA = create_user_and_sounds(num_sounds=4, num_packs=1, tags="tag1 tag2 tag3 tag4 tag5")
        userB, _, _ = create_user_and_sounds(num_sounds=0, num_packs=0,
                                             user=User.objects.create_user("testuser2", password="testpass2"))
        for sound in soundsA:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")

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
        self.assertEqual(sound.is_index_dirty, True)
        self.assertEqual(sound.pack.name, target_sound_pack.name)
        self.assertEqual(sound.pack.num_sounds, 1)
        self.assertEqual(target_sound_pack.num_sounds, 3)
        self.assertEqual(sound.pack.user, userB)

        # Delete original user and perform further checks
        userA.delete()  # Completely delete form db (instead of user.profile.delete_user())
        sound = Sound.objects.get(id=target_sound_id)
        self.assertItemsEqual([ti.id for ti in sound.tags.all()], target_sound_tags)
        calls = [mock.call(i) for i in remaining_sound_ids]
        delete_sound_solr.assert_has_calls(calls)  # All other sounds by the user were deleted


class ProfileNumSoundsTestCase(TestCase):

    fixtures = ['initial_data']

    @mock.patch('sounds.models.delete_sound_from_solr')
    def test_moderation_and_processing_state_changes(self, delete_sound_solr):
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
        delete_sound_solr.assert_called_once_with(sound.id)
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound processed again as ok
        sound.change_moderation_state("DE")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound unmoderated
        self.assertEqual(delete_sound_solr.call_count, 2) # Sound deleted once when going to FA, once when DE

    @mock.patch('sounds.models.delete_sound_from_solr')
    def test_sound_delete(self, delete_sound_solr):
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
        delete_sound_solr.assert_called_once_with(sound_id)

    @mock.patch('sounds.models.delete_sound_from_solr')
    def test_deletedsound_creation(self, delete_sound_solr):
        user, packs, sounds = create_user_and_sounds()
        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        sound_id = sound.id
        sound.delete()
        delete_sound_solr.assert_called_once_with(sound_id)

        self.assertEqual(DeletedSound.objects.filter(sound_id=sound_id).exists(), True)
        ds = DeletedSound.objects.get(sound_id=sound_id)

        # Check this elements are in the json saved on DeletedSound
        keys = ['num_ratings', 'duration', 'id', 'geotag_id', 'comments',
                'base_filename_slug', 'num_downloads', 'md5', 'description',
                'original_path', 'pack_id', 'license', 'created',
                'original_filename', 'geotag']

        json_data = ds.data.keys()
        for k in keys:
            self.assertTrue(k in json_data)

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


class PackNumSoundsTestCase(TestCase):

    fixtures = ['initial_data']

    @mock.patch('sounds.models.delete_sound_from_solr')
    def test_create_and_delete_sounds(self, delete_sound_solr):
        N_SOUNDS = 5
        user, packs, sounds = create_user_and_sounds(num_sounds=N_SOUNDS, num_packs=1)
        pack = packs[0]
        self.assertEqual(pack.num_sounds, 0)
        for count, sound in enumerate(pack.sounds.all()):
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")
            self.assertEqual(Pack.objects.get(id=pack.id).num_sounds, count + 1)  # Check pack has all sounds

        sound_to_delete = sounds[0]
        sound_to_delete_id = sound_to_delete.id
        sound_to_delete.delete()
        delete_sound_solr.assert_called_once_with(sound_to_delete_id)
        self.assertEqual(Pack.objects.get(id=pack.id).num_sounds, N_SOUNDS - 1)  # Check num_sounds on delete sound

    def test_edit_sound(self):
        N_SOUNDS = 1
        user, packs, sounds = create_user_and_sounds(num_sounds=N_SOUNDS, num_packs=1)
        pack = packs[0]
        sound = sounds[0]
        self.assertEqual(pack.num_sounds, 0)
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        self.assertEqual(Pack.objects.get(id=pack.id).num_sounds, 1)  # Check pack has all sounds

        self.client.login(username=user.username, password='testpass')
        resp = self.client.post(reverse('sound-edit', args=[sound.user.username, sound.id]), {
            'submit': [u'submit'],
            'pack-new_pack': [u'new pack name'],
            'pack-pack': [u''],
        })
        self.assertRedirects(resp, reverse('sound', args=[sound.user.username, sound.id]))
        self.assertEqual(Pack.objects.get(id=pack.id).num_sounds, 0)  # Sound changed from pack

    def test_edit_pack(self):
        user, packs, sounds = create_user_and_sounds(num_sounds=4, num_packs=2)
        for sound in sounds:
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")
        pack1 = packs[0]
        pack2 = packs[1]
        self.assertEqual(Pack.objects.get(id=pack1.id).num_sounds, 2)
        self.assertEqual(Pack.objects.get(id=pack2.id).num_sounds, 2)

        # Move one sound from one pack to the other
        sound_ids_pack1 = [s.id for s in pack1.sounds.all()]
        sound_ids_pack2 = [s.id for s in pack2.sounds.all()]
        sound_ids_pack2.append(sound_ids_pack1.pop())
        self.client.login(username=user.username, password='testpass')
        resp = self.client.post(reverse('pack-edit', args=[pack2.user.username, pack2.id]), {
            'submit': [u'submit'],
            'pack_sounds': u','.join([str(sid) for sid in sound_ids_pack2]),
            'name': [u'Test pack 1 (edited)'],
            'description': [u'A new description']
        })
        self.assertRedirects(resp, reverse('pack', args=[pack2.user.username, pack2.id]))
        self.assertEqual(Pack.objects.get(id=pack1.id).num_sounds, 1)
        self.assertEqual(Pack.objects.get(id=pack2.id).num_sounds, 3)

        # Move one sound that had no pack
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=0, user=user, count_offset=5)
        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        resp = self.client.post(reverse('pack-edit', args=[pack2.user.username, pack2.id]), {
            'submit': [u'submit'],
            'pack_sounds':
                u','.join([str(snd.id) for snd in Pack.objects.get(id=pack2.id).sounds.all()] + [str(sound.id)]),
            'name': [u'Test pack 1 (edited again)'],
            'description': [u'A new description']
        })
        self.assertRedirects(resp, reverse('pack', args=[pack2.user.username, pack2.id]))
        self.assertEqual(Pack.objects.get(id=pack1.id).num_sounds, 1)
        self.assertEqual(Pack.objects.get(id=pack2.id).num_sounds, 4)
        self.assertEqual(Sound.objects.get(id=sound.id).pack.id, pack2.id)


class SoundViewsTestCase(TestCase):

    fixtures = ['initial_data']

    @mock.patch('sounds.models.delete_sound_from_solr')
    def test_delete_sound_view(self, delete_sound_solr):
        user, packs, sounds = create_user_and_sounds(num_sounds=1, num_packs=1)
        sound = sounds[0]
        sound_id = sound.id
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        self.client.login(username=user.username, password='testpass')

        # Try delete with incorrect encrypted sound id link (should not delete sound)
        encrypted_link = encrypt(u"%d\t%f" % (1234, time.time()))
        resp = self.client.post(reverse('sound-delete',
            args=[sound.user.username, sound.id]), {"encrypted_link": encrypted_link})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Sound.objects.filter(id=sound_id).count(), 1)

        # Try delete with expired encrypted link (should not delete sound)
        encrypted_link = encrypt(u"%d\t%f" % (sound.id, time.time() - 15))
        resp = self.client.post(reverse('sound-delete',
            args=[sound.user.username, sound.id]), {"encrypted_link": encrypted_link})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Sound.objects.filter(id=sound_id).count(), 1)

        # Try delete with valid link (should delete sound)
        encrypted_link = encrypt(u"%d\t%f" % (sound.id, time.time()))
        resp = self.client.post(reverse('sound-delete',
            args=[sound.user.username, sound.id]), {"encrypted_link": encrypted_link})
        self.assertEqual(Sound.objects.filter(id=sound_id).count(), 0)
        self.assertRedirects(resp, reverse('accounts-home'))
        delete_sound_solr.assert_called_once_with(sound.id)

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
        self.client.login(username=user.username, password='testpass')

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


class RandomSoundTestCase(TestCase):
    """ Test that sounds that don't fall under our criteria don't get selected
        as a random sound."""

    fixtures = ['initial_data']

    def _create_test_sound(self):
        """Create a sound which is suitable for being chosen as a random sound"""
        try:
            user = User.objects.get(username="testuser")
        except User.DoesNotExist:
            user = None
        user, packs, sounds = create_user_and_sounds(num_sounds=1, user=user)
        sound = sounds[0]
        sound.is_explicit = False
        sound.moderation_state = 'OK'
        sound.processing_state = 'OK'
        sound.avg_rating = 8
        sound.num_ratings = 5
        sound.save()

        return sound

    def test_random_sound(self):
        """Correctly selects a random sound"""
        sound = self._create_test_sound()

        random = Sound.objects.random()
        self.assertEqual(random, sound)

    def test_explict(self):
        """Doesn't select a sound if it is marked as explicit"""
        sound = self._create_test_sound()
        sound.is_explicit = True
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

    def test_not_processed(self):
        """Doesn't select a sound if it isn't processed"""
        sound = self._create_test_sound()
        sound.processing_state = 'PE'
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

        # or isn't moderated
        sound = self._create_test_sound()
        sound.moderation_state = 'PE'
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

    def test_ratings(self):
        """Doesn't select a sound if it doesn't have a high enough rating"""
        sound = self._create_test_sound()
        sound.avg_rating = 4
        sound.save()

        random = Sound.objects.random()
        self.assertIsNone(random)

    def test_flag(self):
        """Doesn't select a sound if it's flagged"""
        sound = self._create_test_sound()
        sound.save()
        Flag.objects.create(sound=sound, reporting_user=User.objects.all()[0], email="testemail@freesound.org",
            reason_type="O", reason="Not a good sound")

        random = Sound.objects.random()
        self.assertIsNone(random)


class SoundOfTheDayTestCase(TestCase):

    fixtures = ['sounds', 'email_preference_type']

    def setUp(self):
        cache.clear()

    def test_no_random_sound(self):
        # If we have no sound, return None
        random_sound_id = get_sound_of_the_day_id()
        self.assertIsNone(random_sound_id)
        # TODO: If we have some SoundOfTheDay objects, but not for day, don't return them

    def test_random_sound(self):
        sound = Sound.objects.get(id=19)
        SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date.today())
        random_sound = get_sound_of_the_day_id()
        self.assertEqual(isinstance(random_sound, int), True)

    @freeze_time("2017-06-20")
    def test_create_enough_new_sounds(self):
        """ If we have some random sounds selected for the future, make sure
        that we always have at least settings.NUMBER_OF_RANDOM_SOUNDS_IN_ADVANCE sounds
        waiting in the future."""

        sound_ids = []
        user, packs, sounds = create_user_and_sounds(num_sounds=10)
        for s in sounds:
            sound_ids.append(s.id)

        sound = Sound.objects.get(id=19)
        SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 21))

        call_command("create_random_sound")

        sound_of_days = SoundOfTheDay.objects.count()
        self.assertEqual(sound_of_days, 6)

    def test_send_email_once(self):
        """If we have a SoundOfTheDay, send the sound's user an email, but only once"""
        sound = Sound.objects.get(id=19)
        sotd = SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        sotd.notify_by_email()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "[freesound] One of your sounds has been chosen as random sound of the day!")

        # If we notify again, we don't send another email
        sotd.notify_by_email()
        self.assertEqual(len(mail.outbox), 1)

    def test_user_disable_email_notifications(self):
        """If the chosen Sound's user has disabled email notifications, don't send an email"""
        sound = Sound.objects.get(id=19)
        email_pref = accounts.models.EmailPreferenceType.objects.get(name="random_sound")
        accounts.models.UserEmailSetting.objects.create(user=sound.user, email_type=email_pref)

        sotd = SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        sotd.notify_by_email()

        self.assertEqual(len(mail.outbox), 0)

    @freeze_time("2017-06-20 10:30:00")
    @mock.patch('django.core.cache.cache.set')
    def test_expire_cache_at_end_of_day(self, cache_set):
        """When we cache today's random sound, expire the cache at midnight today"""

        sound = Sound.objects.get(id=19)
        sotd = SoundOfTheDay.objects.create(sound=sound, date_display=datetime.date(2017, 06, 20))
        sound_id = get_sound_of_the_day_id()
        cache_set.assert_called_with("random_sound", 19, 48600)


class DisplaySoundTemplatetagTestCase(TestCase):

    fixtures = ['sounds_with_tags']

    def setUp(self):
        # A sound which has tags
        self.sound = Sound.objects.get(pk=23)

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_sound_from_id(self):
        request = HttpRequest()
        request.user = AnonymousUser()
        Template("{% load display_sound %}{% display_sound sound %}").render(Context({
            'sound': self.sound.id,
            'request': request,
            'media_url': 'http://example.org/'
        }))
        #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_sound_from_obj(self):
        request = HttpRequest()
        request.user = AnonymousUser()
        Template("{% load display_sound %}{% display_sound sound %}").render(Context({
            'sound': self.sound,
            'request': request,
            'media_url': 'http://example.org/'
        }))
        #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    @override_settings(TEMPLATES=[settings.TEMPLATES[0]])
    def test_display_raw_sound(self):
        raw_sound = Sound.objects.bulk_query_id([self.sound.id])[0]
        request = HttpRequest()
        request.user = AnonymousUser()
        Template("{% load display_sound %}{% display_raw_sound sound %}").render(Context({
            'sound': raw_sound,
            'request': request,
            'media_url': 'http://example.org/'
        }))
        #  If the template could not be rendered, the test will have failed by that time, no need to assert anything

    def test_display_sound_wrapper_view(self):
        response = self.client.get(reverse('sound-display', args=[self.sound.user.username, 921]))  # Non existent ID
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse('sound-display', args=[self.sound.user.username, self.sound.id]))
        self.assertEqual(response.status_code, 200)


class SoundPackDownloadTestCase(TestCase):

    fixtures = ['initial_data']

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
            self.assertRedirects(resp, '%s?next=%s' % (
            reverse('login'), reverse('sound', args=[self.sound.user.username, self.sound.id])))

            # Check download works successfully if user logged in
            self.client.login(username=self.user.username, password='testpass')
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
            self.assertEquals(self.user.profile.num_sound_downloads, 1)

            # Delete all Download objects and check num_download attribute of Sound is 0
            Download.objects.all().delete()
            self.sound.refresh_from_db()
            self.assertEqual(self.sound.num_downloads, 0)

            # Check num_sound_downloads in user profile has been updated
            self.user.profile.refresh_from_db()
            self.assertEquals(self.user.profile.num_sound_downloads, 0)

    def test_download_sound_oldusername(self):
        # Test if download works if username changed
        with mock.patch('sounds.views.sendfile', return_value=HttpResponse()):

            self.sound.user.username = 'other_username'
            self.sound.user.save()

            # Check download works successfully if user logged in
            self.client.login(username=self.user.username, password='testpass')
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
            self.assertRedirects(resp, '%s?next=%s' % (
            reverse('login'), reverse('pack', args=[self.sound.user.username, self.pack.id])))

            # Check donwload works successfully if user logged in
            self.client.login(username=self.user.username, password='testpass')
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
            self.assertEquals(self.user.profile.num_pack_downloads, 1)

            # Delete all Download objects and check num_download attribute of Sound is 0
            PackDownload.objects.all().delete()
            self.pack.refresh_from_db()
            self.assertEqual(self.pack.num_downloads, 0)

            # Check num_pack_downloads in user profile has been updated
            self.user.profile.refresh_from_db()
            self.assertEquals(self.user.profile.num_pack_downloads, 0)

    def test_download_pack_oldusername(self):
        # Test if download pack works if username changed
        with mock.patch('sounds.views.sendfile', return_value=HttpResponse()):

            self.pack.user.username = 'other_username'
            self.pack.user.save()

            # Check donwload works successfully if user logged in
            self.client.login(username=self.user.username, password='testpass')

            # First check that the response is a 301
            resp = self.client.get(reverse('pack-download', args=['testuser', self.pack.id]))
            self.assertEqual(resp.status_code, 301)

            # Now follow the redirect
            resp = self.client.get(reverse('pack-download', args=['testuser', self.pack.id]), follow=True)
            self.assertEqual(resp.status_code, 200)

            # Check n download objects is 1
            self.assertEqual(PackDownload.objects.filter(user=self.user, pack=self.pack).count(), 1)


class SoundSignatureTestCase(TestCase):

    fixtures = ['initial_data']

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
        self.client.login(username='testuser', password='testpass')
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertNotContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)

        # Logged-in user (non-creator of the sound)
        self.client.login(username='testuservisitor', password='testpassword')
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
        self.client.login(username='testuser', password='testpass')
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)

        # Logged-in user (non-creator of the sound)
        self.client.login(username='testuservisitor', password='testpassword')
        resp = self.client.get(reverse('sound', args=[self.sound.user.username, self.sound.id]))
        self.assertContains(resp, self.SOUND_DESCRIPTION, status_code=200, html=True)
        self.assertContains(resp, self.USER_SOUND_SIGNATURE, status_code=200, html=True)


class SoundTemplateCacheTests(TestCase):
    fixtures = ['initial_data']

    def setUp(self):
        cache.clear()
        user, packs, sounds = create_user_and_sounds(num_sounds=1)
        self.sound = sounds[0]
        self.sound.change_processing_state("OK")
        self.sound.change_moderation_state("OK")
        self.user = user

    def _get_sound_view_cache_keys(self, is_explicit=False, display_random_link=False):
        return ([get_template_cache_key('sound_footer_bottom', self.sound.id),
                get_template_cache_key('sound_header', self.sound.id, is_explicit)] +
                self._get_sound_view_footer_top_cache_keys(display_random_link))

    def _get_sound_view_footer_top_cache_keys(self, display_random_link=False):
        return [get_template_cache_key('sound_footer_top', self.sound.id, display_random_link)]

    def _get_sound_display_cache_keys(self, is_authenticated=True, is_explicit=False):
        return [get_template_cache_key('display_sound', self.sound.id, is_authenticated, is_explicit)]

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

    def _get_sound_from_home(self):
        return self.client.get(reverse('accounts-home'))

    def _print_cache(self, cache_keys):
        print(locmem._caches[''].keys())
        print(cache_keys)

    # Make sure the sound name and description are updated
    def test_update_description(self):
        cache_keys = self._get_sound_view_cache_keys()
        self._assertCacheAbsent(cache_keys)

        # Test as an authenticated user, although it doesn't matter in this case because cache templates are the same
        # for both logged in and anonymous user.
        self.client.login(username='testuser', password='testpass')

        resp = self._get_sound_view()
        self.assertEqual(resp.status_code, 200)
        self._assertCachePresent(cache_keys)

        # Edit sound
        new_description = u'New description'
        new_name = u'New name'
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            'description-description': new_description,
            'description-name': new_name,
            'description-tags': u'tag1 tag2 tag3'
        })
        self.assertEqual(resp.status_code, 302)

        # Check that keys are no longer in cache
        self._assertCacheAbsent(cache_keys)

        # Check that the information is updated properly
        resp = self._get_sound_view()
        self.assertEqual(resp.status_code, 200)
        self.assertInHTML(new_description, resp.content)
        self.assertInHTML(new_name, resp.content)

    def _get_delete_comment_url(self, html):
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find('a', {'id': 'delete_button'})
        return tag['href']

    # Comments are only cached in display
    def test_add_remove_comment(self):
        cache_keys = self._get_sound_display_cache_keys()
        self._assertCacheAbsent(cache_keys)
        self.client.login(username='testuser', password='testpass')

        # Check the initial state (0 comments)
        resp = self._get_sound_from_home()
        self.assertInHTML('0 comments', resp.content)
        self.assertEqual(resp.status_code, 200)
        self._assertCachePresent(cache_keys)

        # Add comment
        resp = self.client.post(self._get_sound_url('sound'), {
            'comment': u'Test comment'
        }, follow=True)  # we are testing sound-display, rendering sound view is ok
        delete_url = self._get_delete_comment_url(resp.content)
        self._assertCacheAbsent(cache_keys)

        # Verify that sound display has updated number of comments
        resp = self._get_sound_from_home()
        self.assertInHTML('1 comment', resp.content)
        self._assertCachePresent(cache_keys)

        # Delete the comment
        resp = self.client.get(delete_url)
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Verify that sound display has no comments
        resp = self._get_sound_from_home()
        self.assertInHTML('0 comments', resp.content)

    # Downloads are only cached in display
    @mock.patch('sounds.views.sendfile', return_value=HttpResponse('Dummy response'))
    def test_download(self, sendfile):
        cache_keys = self._get_sound_display_cache_keys()
        self._assertCacheAbsent(cache_keys)

        self.client.login(username='testuser', password='testpass')

        resp = self._get_sound_from_home()
        self.assertInHTML('0 downloads', resp.content)
        self.assertEqual(resp.status_code, 200)
        self._assertCachePresent(cache_keys)

        # Download
        resp = self.client.get(self._get_sound_url('sound-download'))
        sendfile.assert_called_once_with(self.sound.locations("path"),
                                         self.sound.friendly_filename(),
                                         self.sound.locations("sendfile_url"))
        self.assertEqual(resp.status_code, 200)
        self._assertCacheAbsent(cache_keys)

        # Verify that sound display has updated number of downloads
        resp = self._get_sound_from_home()
        self.assertInHTML('1 download', resp.content)

    # Similarity link (cached in display and view)
    @mock.patch('general.management.commands.similarity_update.Similarity.add', return_value='Dummy response')
    def _test_similarity_update(self, cache_keys, check_present, similarity_add):
        # Default analysis_state is 'PE', but for similarity update it should be 'OK', otherwise sound gets ignored
        self.sound.analysis_state = 'OK'
        self.sound.save()

        self._assertCacheAbsent(cache_keys)

        self.client.login(username='testuser', password='testpass')

        # Initial check
        self.assertEqual(self.sound.similarity_state, 'PE')
        self.assertFalse(check_present())
        self._assertCachePresent(cache_keys)

        # Update similarity
        call_command('similarity_update', freesound_extractor_version=None)
        similarity_add.assert_called_once_with(self.sound.id, self.sound.locations('analysis.statistics.path'))
        self._assertCacheAbsent(cache_keys)

        # Check similarity icon
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.similarity_state, 'OK')
        self.assertTrue(check_present())

    def test_similarity_update_display(self):
        self._test_similarity_update(
            self._get_sound_display_cache_keys(),
            lambda: '<a class="similar"' in self._get_sound_from_home().content)

    def test_similarity_update_view(self):
        self._test_similarity_update(
            self._get_sound_view_footer_top_cache_keys(),
            lambda: '<a id="similar_sounds_link"' in self._get_sound_view().content)

    # Pack link (cached in display and view)
    def _test_add_remove_pack(self, cache_keys, check_present):
        self._assertCacheAbsent(cache_keys)

        self.client.login(username='testuser', password='testpass')

        self.assertIsNone(self.sound.pack)
        self.assertFalse(check_present())
        self._assertCachePresent(cache_keys)

        # Add sound to pack
        pack_name = 'New pack'
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            'pack-new_pack': pack_name,
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check pack icon
        self.sound.refresh_from_db()
        self.assertIsNotNone(self.sound.pack)
        self.assertTrue(check_present())  # check_present should render the template
        self._assertCachePresent(cache_keys)

        # Remove sound from pack
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            'pack-pack': '',
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check pack icon being absent
        self.sound.refresh_from_db()
        self.assertIsNone(self.sound.pack)
        self.assertFalse(check_present())

    def test_add_remove_pack_display(self):
        self._test_add_remove_pack(
            self._get_sound_display_cache_keys(),
            lambda: '<a class="pack"' in self._get_sound_from_home().content
        )

    def test_add_remove_pack_view(self):
        self._test_add_remove_pack(
            self._get_sound_view_footer_top_cache_keys(),
            lambda: '<a id="pack_link"' in self._get_sound_view().content
        )

    # Geotag link (cached in display and view)
    def _test_add_remove_geotag(self, cache_keys, check_present):
        self._assertCacheAbsent(cache_keys)

        self.client.login(username='testuser', password='testpass')

        self.assertIsNone(self.sound.geotag)
        self.assertFalse(check_present())
        self._assertCachePresent(cache_keys)

        # Add a geotag to the sound
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            'geotag-lat': 20,
            'geotag-lon': 20,
            'geotag-zoom': 18
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check geotag icon
        self.sound.refresh_from_db()
        self.assertIsNotNone(self.sound.geotag)
        self.assertTrue(check_present())
        self._assertCachePresent(cache_keys)

        # Remove geotag from the sound
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            'geotag-remove_geotag': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check geotag icon being absent
        self.sound.refresh_from_db()
        self.assertIsNone(self.sound.geotag)
        self.assertFalse(check_present())

    def test_add_remove_geotag_display(self):
        self._test_add_remove_geotag(
            self._get_sound_display_cache_keys(),
            lambda: '<a class="geotag"' in self._get_sound_from_home().content
        )

    def test_add_remove_geotag_view(self):
        self._test_add_remove_geotag(
            self._get_sound_view_footer_top_cache_keys(),
            lambda: '<a id="geotag_link"' in self._get_sound_view().content
        )

    # Changing license
    def _test_change_license(self, cache_keys, new_license, check_present):
        self._assertCacheAbsent(cache_keys)

        self.client.login(username='testuser', password='testpass')

        self.assertNotEqual(self.sound.license, new_license)
        self.assertFalse(check_present())
        self._assertCachePresent(cache_keys)

        # Change license
        resp = self.client.post(self._get_sound_url('sound-edit'), {
            'license': new_license.id,
        })
        self.assertEqual(resp.status_code, 302)
        self._assertCacheAbsent(cache_keys)

        # Check that license is updated
        self.assertTrue(check_present())

    def test_change_license_display(self):
        self._test_change_license(
            self._get_sound_display_cache_keys(),
            License.objects.get(name='Attribution'),
            lambda: 'images/licenses/by.png' in self._get_sound_from_home().content
        )

    def test_change_license_view(self):
        license = License.objects.get(name='Attribution')
        self._test_change_license(
            self._get_sound_view_footer_top_cache_keys(),
            license,
            lambda: str(license.name) in self._get_sound_view().content
        )

    def _test_add_remove_remixes(self, cache_keys, check_present):
        _, _, sounds = create_user_and_sounds(num_sounds=1, user=self.user)
        another_sound = sounds[0]
        self._assertCacheAbsent(cache_keys)

        self.client.login(username='testuser', password='testpass')

        self.assertEqual(self.sound.remix_group.count(), 0)
        self.assertFalse(check_present())
        self._assertCachePresent(cache_keys)

        # Indicate another sound as source
        resp = self.client.post(self._get_sound_url('sound-edit-sources'), {
            'sources': str(another_sound.id)
        })
        self.assertEqual(resp.status_code, 200)
        call_command('create_remix_groups')
        self._assertCacheAbsent(cache_keys)

        # Check remix icon
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.remix_group.count(), 1)
        self.assertTrue(check_present())
        self._assertCachePresent(cache_keys)

        # Remove remix from the sound
        resp = self.client.post(self._get_sound_url('sound-edit-sources'), {
            'sources': ''
        })
        self.assertEqual(resp.status_code, 200)
        call_command('create_remix_groups')
        self._assertCacheAbsent(cache_keys)

        # Check remix icon being absent
        self.sound.refresh_from_db()
        self.assertEquals(self.sound.remix_group.count(), 0)
        self.assertFalse(check_present())

    def test_add_remove_remixes_display(self):
        self._test_add_remove_remixes(
            self._get_sound_display_cache_keys(),
            lambda: '<a class="remixes"' in self._get_sound_from_home().content
        )

    def test_add_remove_remixes_view(self):
        self._test_add_remove_remixes(
            self._get_sound_view_footer_top_cache_keys(),
            lambda: '<a id="remixes_link"' in self._get_sound_view().content
        )

    def _test_state_change(self, cache_keys, change_state, check_present):
        """@:param check_present - function that checks presence of indication of not 'OK' state"""
        self.client.login(username='testuser', password='testpass')

        self._assertCacheAbsent(cache_keys)
        self.assertTrue(check_present())
        self._assertCachePresent(cache_keys)

        # Change processing state
        change_state()

        self._assertCacheAbsent(cache_keys)
        self.assertFalse(check_present())
        self._assertCachePresent(cache_keys)

    def test_processing_state_change_display(self):
        self.sound.change_processing_state('PE')
        self._test_state_change(
            self._get_sound_display_cache_keys(),
            lambda: self.sound.change_processing_state('OK'),
            lambda: all([text in self.client.get(self._get_sound_url('sound-display')).content
                         for text in ['Processing state:', 'Pending']])
        )

    def test_moderation_state_change_display(self):
        self.sound.change_moderation_state('PE')
        self._test_state_change(
            self._get_sound_display_cache_keys(),
            lambda: self.sound.change_moderation_state('OK'),
            lambda: all([text in self.client.get(self._get_sound_url('sound-display')).content
                         for text in ['Moderation state:', 'Pending']])
        )


class SoundAnalysisModel(TestCase):

    fixtures = ['initial_data']

    @override_settings(ANALYSIS_PATH=tempfile.mkdtemp())
    def test_get_analysis(self):
        _, _, sounds = create_user_and_sounds(num_sounds=1)
        sound = sounds[0]
        analysis_data = {'descriptor1': 0.56, 'descirptor2': 1.45, 'descriptor3': 'label'}

        # Create one analysis object that stores the data in the model. Check that get_analysis returns correct data.
        sa = SoundAnalysis.objects.create(sound=sound, extractor="TestExtractor1", analysis_data=analysis_data)
        self.assertEquals(sound.analyses.all().count(), 1)
        self.assertEquals(sa.get_analysis().keys(), analysis_data.keys())
        self.assertEquals(sa.get_analysis()['descriptor1'], 0.56)

        # Now create an analysis object which stores output in a JSON file. Again check that get_analysis works.
        analysis_filename = '%i_testextractor_out.json'
        sound_analysis_folder = os.path.join(settings.ANALYSIS_PATH, str(sound.id / 1000))
        os.mkdir(sound_analysis_folder)
        json.dump(analysis_data, open(os.path.join(sound_analysis_folder, analysis_filename), 'w'))
        sa2 = SoundAnalysis.objects.create(sound=sound, extractor="TestExtractor2", analysis_filename=analysis_filename)
        self.assertEquals(sound.analyses.all().count(), 2)
        self.assertEquals(sa2.get_analysis().keys(), analysis_data.keys())
        self.assertEquals(sa2.get_analysis()['descriptor1'], 0.56)

        # Create an analysis object which refeences a non-existing file. Check that get_analysis returns None.
        sa3 = SoundAnalysis.objects.create(sound=sound, extractor="TestExtractor3",
                                           analysis_filename='non_existing_file.json')
        self.assertEquals(sound.analyses.all().count(), 3)
        self.assertEquals(sa3.get_analysis(), None)


class SoundManagerQueryMethods(TestCase):

    fixtures = ['initial_data']

    fields_to_check_bulk_query_id = ['username', 'id', 'type', 'user_id', 'original_filename', 'is_explicit',
                                     'avg_rating', 'num_ratings', 'description', 'moderation_state', 'processing_state',
                                     'processing_ongoing_state', 'similarity_state', 'created', 'num_downloads',
                                     'num_comments', 'pack_id', 'duration', 'pack_name', 'license_id', 'license_name',
                                     'license_deed_url', 'geotag_id', 'remixgroup_id', 'ac_analysis', 'tag_array']

    fields_to_check_bulk_query_solr = ['username', 'user_id', 'id', 'type', 'original_filename', 'is_explicit',
                                       'filesize', 'md5', 'channels', 'avg_rating', 'num_ratings', 'description',
                                       'created', 'num_downloads', 'num_comments', 'duration', 'pack_id', 'geotag_id',
                                       'bitrate', 'bitdepth', 'samplerate', 'pack_name', 'license_name', 'geotag_lat',
                                       'geotag_lon', 'ac_analysis', 'is_remix', 'was_remixed', 'tag_array',
                                       'comments_array']

    def setUp(self):
        _, _, sounds = create_user_and_sounds(num_sounds=3, tags="tag1 tag2 tag3")
        self.sounds = sounds
        self.sound_ids = [s.id for s in sounds]

    def test_bulk_query_id_num_queries(self):

        # Check that all fields for each sound are retrieved with one query
        with self.assertNumQueries(1):
            for sound in Sound.objects.bulk_query_id(sound_ids=self.sound_ids):
                for field in self.fields_to_check_bulk_query_id:
                    self.assertTrue(hasattr(sound, field), True)

    def test_bulk_query_id_field_contents(self):

        # Check the contents of some fields are correct
        for i, sound in enumerate(Sound.objects.bulk_query_id(sound_ids=self.sound_ids)):
            self.assertEqual(self.sounds[i].user.username, sound.username)
            # TODO: add more field checks here

    def test_bulk_query_solr_num_queries(self):

        # Check that all fields for each sound are retrieved with one query
        with self.assertNumQueries(1):
            for sound in Sound.objects.bulk_query_solr(sound_ids=self.sound_ids):
                for field in self.fields_to_check_bulk_query_solr:
                    self.assertTrue(hasattr(sound, field), True)

    def test_bulk_query_solr_field_contents(self):

        # Check the contents of some fields are correct
        for i, sound in enumerate(Sound.objects.bulk_query_solr(sound_ids=self.sound_ids)):
            self.assertEqual(self.sounds[i].user.username, sound.username)
            # TODO: add more field checks here
