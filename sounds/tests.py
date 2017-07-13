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

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from sounds.models import Sound, Pack, License, DeletedSound
from sounds.views import get_random_sound, get_random_uploader
from general.templatetags.filter_img import replace_img
from utils.tags import clean_and_split_tags
from utils.encryption import encrypt
import time


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
        random_sound = get_random_sound()
        self.assertEqual(isinstance(random_sound, int), True)

    def test_random_uploader(self):
        # Update num_sounds in user profile data
        for u in User.objects.all():
            profile = u.profile
            profile.num_sounds = u.sounds.all().count()
            profile.save()
        random_uploader = get_random_uploader()
        self.assertEqual(isinstance(random_uploader, User), True)


class CommentSoundsTestCase(TestCase):

    fixtures = ['sounds']

    def test_add_comment(self):
        sound = Sound.objects.get(id=19)
        user = User.objects.get(id=2)
        current_num_comments = sound.num_comments
        self.assertEqual(current_num_comments, sound.num_comments)
        sound.add_comment(user, "Test comment")
        sound.refresh_from_db()
        self.assertEqual(current_num_comments + 1, sound.num_comments)
        self.assertEqual(sound.is_index_dirty, True)

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


def create_user_and_sounds(num_sounds=1, num_packs=0, user=None, count_offset=0, tags=None):
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


class ChanegSoundOwnerTestCase(TestCase):

    fixtures = ['initial_data']

    def test_change_sound_owner(self):
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

        # Change owenership of sound
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


class ProfileNumSoundsTestCase(TestCase):

    fixtures = ['initial_data']

    def test_moderation_and_processing_state_changes(self):
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
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound processed again as ok
        sound.change_moderation_state("DE")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound unmoderated

    def test_sound_delete(self):
        user, packs, sounds = create_user_and_sounds()
        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)
        sound.delete()
        self.assertEqual(user.profile.num_sounds, 0)

    def test_deletedsound_creation(self):
        user, packs, sounds = create_user_and_sounds()
        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        sound_id = sound.id
        sound.delete()

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

    def test_create_and_delete_sounds(self):
        N_SOUNDS = 5
        user, packs, sounds = create_user_and_sounds(num_sounds=N_SOUNDS, num_packs=1)
        pack = packs[0]
        self.assertEqual(pack.num_sounds, 0)
        for count, sound in enumerate(pack.sound_set.all()):
            sound.change_processing_state("OK")
            sound.change_moderation_state("OK")
            self.assertEqual(Pack.objects.get(id=pack.id).num_sounds, count + 1)  # Check pack has all sounds

        sounds[0].delete()
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
        sound_ids_pack1 = [s.id for s in pack1.sound_set.all()]
        sound_ids_pack2 = [s.id for s in pack2.sound_set.all()]
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
                u','.join([str(snd.id) for snd in Pack.objects.get(id=pack2.id).sound_set.all()] + [str(sound.id)]),
            'name': [u'Test pack 1 (edited again)'],
            'description': [u'A new description']
        })
        self.assertRedirects(resp, reverse('pack', args=[pack2.user.username, pack2.id]))
        self.assertEqual(Pack.objects.get(id=pack1.id).num_sounds, 1)
        self.assertEqual(Pack.objects.get(id=pack2.id).num_sounds, 4)
        self.assertEqual(Sound.objects.get(id=sound.id).pack.id, pack2.id)


class SoundViewsTestCase(TestCase):

    fixtures = ['initial_data']

    def test_delete_sound_view(self):
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

        # Try delete with expried encrypted link (should not delete sound)
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
