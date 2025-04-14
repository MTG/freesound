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

import logging

from django.conf import settings
from django.core.cache import cache

from geotags.views import generate_bytearray
from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger('console')


class Command(LoggingBaseCommand):

    help = 'Generate byetearray for "all geoatgs map page" at cache it'

    def handle(self, *args, **options):
        self.log_start()

        # Generate the bytearray for all geotagged sounds in Freesound and store it in cache
        # Don't set expiration time because the bytearray will be overwritten everytime this command runs
        sounds = Sound.objects.select_related('geotag').exclude(geotag=None)
        count = sounds.count()
        computed_bytearray, num_geotags = generate_bytearray(sounds.all())
        cache.set(settings.ALL_GEOTAGS_BYTEARRAY_CACHE_KEY, [computed_bytearray, num_geotags], timeout=None)
        console_logger.info(f'Generated all geotags bytearray with {count} sounds')

        self.log_end({'all_geotags_bytearray_n_sounds': count})
