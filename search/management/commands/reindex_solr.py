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

from sounds.models import Sound
from utils.search.search_general import add_all_sounds_to_solr, delete_sound_from_solr

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    args = ''
    help = 'Take all sounds moderated and processed as OK and send them to Solr'

    def add_arguments(self, parser):
        parser.add_argument(
            '-a', '--mark_all_sounds',
            action='store',
            dest='mark_all_sounds',
            default=1,
            help='Mark all sounds as index clean.')

    def handle(self, *args, **options):
        mark_all_sounds = options['mark_all_sounds'] != "0"

        # Get all sounds moderated and processed ok
        sounds_to_index = Sound.objects.filter(processing_state="OK", moderation_state="OK")
        console_logger.info("Reindexing %d sounds to solr", sounds_to_index.count())

        add_all_sounds_to_solr(sounds_to_index, mark_index_clean=mark_all_sounds)

        # Get all sounds that should not be in solr and remove them if they are
        sound_qs = Sound.objects.exclude(processing_state="OK", moderation_state="OK")
        for sound in sound_qs:
            delete_sound_from_solr(sound.id)  # Will only do something if sound in fact exists in solr
