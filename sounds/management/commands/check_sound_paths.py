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
import logging
import os

from django.core.management.base import BaseCommand

from sounds.models import Sound

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = 'Checks that the original audio files for sound objects exist in disk.' \
           'If an --outfile option is provided with a file path, the IDs of the sounds with missing audio files will' \
           'be saved in that file in disk.'

    def add_arguments(self, parser):
        parser.add_argument('-o', '--outfile', type=str, default=None, help='File path where to store the IDs of sounds'
                                                                            ' with missing files (if any)')

    def handle(self, *args, **options):

        missing_sound_ids = []
        for sound in Sound.objects.all().iterator():
            if not os.path.exists(sound.locations('path')):
                missing_sound_ids += [sound.id]

        console_logger.info(f'Found {len(missing_sound_ids)} sounds with missing audio files')

        if missing_sound_ids and options['outfile'] is not None:
            json.dump(missing_sound_ids, open(options['outfile'], 'w'))
            console_logger.info(f"List of sound IDs with missing files saved in \"{options['outfile']}\"")
