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
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from sounds.models import Sound, Pack, License
from sounds.views import get_random_sound, get_random_uploader
from comments.models import Comment
import mock
import gearman


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
        comment = Comment(content_object=sound,
                          user=user,
                          comment="Test comment")
        sound.add_comment(comment)
        self.assertEqual(comment.id in [c.id for c in sound.comments.all()], True)
        self.assertEqual(current_num_comments + 1, sound.num_comments)
        self.assertEqual(sound.is_index_dirty, True)

    def test_post_delete_comment(self):
        sound = Sound.objects.get(id=19)
        sound.is_index_dirty = False
        sound.num_comments = 3
        sound.save()
        sound.post_delete_comment()
        self.assertEqual(2, sound.num_comments)
        self.assertEqual(sound.is_index_dirty, True)


def create_user_and_sounds(num_sounds=1):
    user = User.objects.create_user("testuser", password="testpass")
    sounds = list()
    for i in range(0, num_sounds):
        sound = Sound.objects.create(user=user,
                                     original_filename="Test sound %i" % i,
                                     license=License.objects.all()[0],
                                     md5="fakemd5_%i" % i)
        sounds.append(sound)
    return user, sounds


class ProfileNumSoundsTestCase(TestCase):

    fixtures = ['initial_data']

    # TODO: Test that num_sounds in user profile is updated acordingly when:
    #   4) num_sounds NOT updated when a sound is reprocessed and processing_state does not change
    #   5) A pack is deleted

    def test_moderation_and_processing_state_changes(self):
        user, sounds = create_user_and_sounds()
        sound = sounds[0]
        self.assertEqual(user.profile.num_sounds, 0)  # Sound not yet moderated or processed
        sound.change_moderation_state("OK")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound not yet processed
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound now processed and moderated
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound reprocessed and again set as ok
        sound.change_processing_state("FA")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound failed processing
        sound.change_processing_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)  # Sound processed again as ok
        sound.change_moderation_state("DE")
        self.assertEqual(user.profile.num_sounds, 0)  # Sound unmoderated

    def test_sound_delete(self):
        user, sounds = create_user_and_sounds()
        sound = sounds[0]
        sound.change_processing_state("OK")
        sound.change_moderation_state("OK")
        self.assertEqual(user.profile.num_sounds, 1)
        sound.delete()
        self.assertEqual(user.profile.num_sounds, 0)








