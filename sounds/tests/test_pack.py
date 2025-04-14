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


from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
import pytest

from general.templatetags.filter_img import replace_img
from sounds.models import Pack, Sound
from utils.cache import get_template_cache_key
from utils.test_helpers import create_user_and_sounds, override_analysis_path_with_temp_directory


class PackNumSoundsTestCase(TestCase):

    fixtures = ['licenses']

    @mock.patch('sounds.models.delete_sounds_from_search_engine')
    def test_create_and_delete_sounds(self, delete_sounds_from_search_engine):
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
        delete_sounds_from_search_engine.assert_called_once_with([sound_to_delete_id])
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

        self.client.force_login(user)
        resp = self.client.post(reverse('sound-edit', args=[sound.user.username, sound.id]), {
            '0-sound_id': sound.id,
            '0-bst_category': 'ss-n',
            '0-description': 'this is a description for the sound',
            '0-name': sound.original_filename,
            '0-tags': 'tag1 tag2 tag3',
            '0-license': '3',
            '0-new_pack': 'new pack name',
            '0-pack': ''
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
        self.client.force_login(user)
        resp = self.client.post(reverse('pack-edit', args=[pack2.user.username, pack2.id]), {
            'pack_sounds': ','.join([str(sid) for sid in sound_ids_pack2]),
            'name': 'Test pack 1 (edited)',
            'description': 'A new description'
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
            'pack_sounds':
                ','.join([str(snd.id) for snd in Pack.objects.get(id=pack2.id).sounds.all()] + [str(sound.id)]),
            'name': 'Test pack 1 (edited again)',
            'description': 'A new description'
        })
        self.assertRedirects(resp, reverse('pack', args=[pack2.user.username, pack2.id]))
        self.assertEqual(Pack.objects.get(id=pack1.id).num_sounds, 1)
        self.assertEqual(Pack.objects.get(id=pack2.id).num_sounds, 4)
        self.assertEqual(Sound.objects.get(id=sound.id).pack.id, pack2.id)

class PackViewsTestCase(TestCase):

    fixtures = ['licenses', 'sounds_with_tags']

    def test_pack_view(self):
        pack = Pack.objects.get(id=5103)
        resp = self.client.get(reverse('pack', args=[pack.user.username, pack.id]))
        assert resp.status_code == 200

    def test_pack_bad_username_in_url(self):
        """username is different to that of the pack"""

        pack = Pack.objects.get(id=5103)
        # user needs to exist anyway, for the redirect_if_old_username_or_404 decorator
        username = pack.user.username + 'xxxx'
        User.objects.create_user(username=username)
        url = reverse('pack', args=[username, pack.id])
        resp = self.client.get(url)
        assert resp.status_code == 404

    def test_pack_view_no_pack(self):
        """pack id does not exist"""
        
        # user needs to exist anyway, for the redirect_if_old_username_or_404 decorator
        username = 'user'
        User.objects.create_user(username=username)
        url = reverse('pack', args=[username, 9999999])
        resp = self.client.get(url)
        assert resp.status_code == 404


@pytest.mark.django_db
class PackStatsSectionTest:

    def test_get_total_pack_sounds_length(self, use_dummy_cache_backend, client):
        call_command('loaddata', 'licenses', 'sounds')
        pack = Pack.objects.all()[0]

        response = client.get(reverse('pack-stats-section', kwargs={'username': pack.user.username, 'pack_id': pack.id}) + '?ajax=1')
        assert response.status_code == 200
        assert "0:21 minutes" in response.content.decode('utf-8')

        sound = pack.sounds.all()[0]
        sound.duration = 1260
        sound.save()
        response = client.get(reverse('pack-stats-section', kwargs={'username': pack.user.username, 'pack_id': pack.id}) + '?ajax=1')
        assert "21:16 minutes" in response.content.decode('utf-8')
