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

from django.conf import settings
from django.test import TestCase

from sounds.models import Pack


class TestPack(TestCase):
    fixtures = ['licenses', 'sounds']

    def test_get_total_pack_sounds_length(self):
        pack = Pack.objects.all()[0]
        self.assertEqual(pack.get_total_pack_sounds_length(), {'formatted_length': '0:21', 'length_text': 'minutes'})

        sound = pack.sounds.all()[0]
        sound.duration = 1260
        sound.save()
        self.assertEqual(pack.get_total_pack_sounds_length(), {'formatted_length': '21:16', 'length_text': 'minutes'})

        sound.duration = 3600 + 1260
        sound.save()
        self.assertEqual(pack.get_total_pack_sounds_length(), {'formatted_length': '1:21', 'length_text': 'hours'})
