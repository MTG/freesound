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
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from utils.forms import filename_has_valid_extension
from sounds.models import Sound, Pack, License, DeletedSound

import utils.downloads

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
            sound = Sound.objects.create(user=user,
                                     original_filename="Test sound %i" % (i),
                                     base_filename_slug="test_sound_%i" % (i),
                                     license=License.objects.all()[0],
                                     pack=pack,
                                     md5="fakemd5_%i" % (i))
        licenses_url = (reverse('pack-licenses', args=["testuser", pack.id]))
        ret = utils.downloads.download_sounds(licenses_url, pack)
        self.assertEqual(ret.status_code, 200)
