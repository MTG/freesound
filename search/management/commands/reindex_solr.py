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
from utils.search.search_general import add_all_sounds_to_search_engine, delete_sounds_from_search_engine, get_all_sound_ids_from_search_engine

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    args = ''
    help = 'Take all sounds moderated and processed as OK and send them to the search engine. Delete existing previous versions of' \
           'these same sounds before indexing (if existing) and also delete extra sounds in the search engine which are not found ' \
           'in DB. All this process is in slices of sounds so that in case of updating existing indexed sounds the ' \
           'index never is fully emptied but we iteratively delete XYZ and re-index XYZ. This command can be used in' \
           'case there is a specific need of re-indexing all sounds without marking them as is_index_dirty and ' \
           'using the "post_dirty_sounds_to_solr" command.'

    def handle(self, *args, **options):

        # Get all sounds moderated and processed ok and add them to the search engine (also delete them before re-indexing)
        sounds_to_index = Sound.objects.filter(processing_state="OK", moderation_state="OK")
        console_logger.info("Re-indexing %d sounds to the search engine", sounds_to_index.count())
        add_all_sounds_to_search_engine(sounds_to_index, mark_index_clean=True, delete_if_existing=True)

        # Delete all sounds in the search engine which are not found in the Freesound DB
        search_engine_ids = get_all_sound_ids_from_search_engine()
        indexed_sound_ids = sounds_to_index.values_list('id', flat=True)
        sound_ids_to_delete = list(set(search_engine_ids).difference(indexed_sound_ids))
        console_logger.info("Deleting %d non-existing sounds form the search engine", len(sound_ids_to_delete))
        delete_sounds_from_search_engine(sound_ids=sound_ids_to_delete)
