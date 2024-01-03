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
from search.management.commands.post_dirty_sounds_to_search_engine import send_sounds_to_search_engine
from utils.search.search_sounds import delete_all_sounds_from_search_engine, delete_sounds_from_search_engine, get_all_sound_ids_from_search_engine

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = 'Take all sounds moderated and processed as OK and index them in the search engine. If there are remaining ' \
           'sounds in the search engine which are not in the DB, delete them as well.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slize_size', dest='size_size', default=4000, type=int, help='How many sounds to add at once'
        )

        parser.add_argument(
            '-c',
            '--clear_index',
            action='store_true',
            dest='clear_index',
            default=False,
            help='Clear all sounds in the existing index before re-indexing all sounds. This option is normally not '
            'needed as the command will clean any leftover sounds from the search index which are no longer'
            'in the DB.'
        )

    def handle(self, *args, **options):
        # Get all indexed sound IDs and remove them
        clear_index = options['clear_index']
        if clear_index:
            delete_all_sounds_from_search_engine()

        # Get all sounds moderated and processed ok and add them to the search engine
        # Don't delete existing sounds in each loop because we clean up in the final step
        sounds_to_index_ids = list(
            Sound.objects.filter(processing_state="OK", moderation_state="OK").values_list('id', flat=True)
        )
        console_logger.info("Re-indexing %d sounds to the search engine", len(sounds_to_index_ids))
        send_sounds_to_search_engine(sounds_to_index_ids, slice_size=options['size_size'], delete_if_existing=False)

        # Delete all sounds in the search engine which are not found in the DB. This part of code is to make sure that
        # no "leftover" sounds remain in the search engine, but should normally do nothing, specially if the
        # "clear_index" option is passed
        indexed_sound_ids = get_all_sound_ids_from_search_engine()
        sound_ids_to_delete = list(set(indexed_sound_ids).difference(sounds_to_index_ids))
        console_logger.info("Deleting %d non-existing sounds from the search engine", len(sound_ids_to_delete))
        if sound_ids_to_delete:
            delete_sounds_from_search_engine(sound_ids_to_delete)
