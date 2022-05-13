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

from django.core.management.base import BaseCommand

from django.core.cache import caches

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = "Clears all the cache entries related to sound/pack templates"

    def handle(self, **options):
        # Get default cache, as this is where sound template entries are stored
        cache = caches['default']
        all_keys= cache.keys('*')
        keys_to_delete = [key for key in all_keys if 'template' in key and ('sound' in key or 'pack' in key)]
        total = len(keys_to_delete)
        console_logger.info('Will clear {} keys from cache'.format(total))
        for count, key in enumerate(keys_to_delete):
            cache.delete(key)
            if count % 1000 == 0:
                console_logger.info('{}/{}'.format(count + 1, total))
