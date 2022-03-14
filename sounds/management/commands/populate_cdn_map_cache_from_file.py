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

from django.core.cache import caches
from django.core.management.base import BaseCommand


cache_cdn_map = caches["cdn_map"]


class Command(BaseCommand):

    help = 'Populate the cdn map cache for sound downloads using a JSON file with the mapping'

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='Path to JSON file with sounds map')
        parser.add_argument('-d', help='First clear the existing records in the cache (if any)')
        
    def handle(self, *args, **options):
        file_path = options['filepath']
        delete_already_existing = options['d']        
        map_data = json.load(open(file_path))

        if delete_already_existing:
            cache_cdn_map.clear()
        
        for sound_id, cdn_filename in map_data:
            cache_cdn_map.set(str(sound_id), cdn_filename, timeout=None)  # No expiration

        print('Done loading {} items to cache'.format(len(map_data)))
