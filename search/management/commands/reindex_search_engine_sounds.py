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
import json
import datetime
import os

from django.core.management.base import BaseCommand

from sounds.models import Sound
from search.management.commands.post_dirty_sounds_to_search_engine import send_sounds_to_search_engine
from utils.search.search_sounds import delete_all_sounds_from_search_engine, delete_sounds_from_search_engine, get_all_sound_ids_from_search_engine
from search import solrapi

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = 'Take all sounds moderated and processed as OK and index them in the search engine. If there are remaining ' \
           'sounds in the search engine which are not in the DB, delete them as well.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slize_size',
            dest='size_size',
            default=500,
            type=int,
            help='How many sounds to add at once')

        parser.add_argument(
            '-c', '--clear_index',
            action='store_true',
            dest='clear_index',
            default=False,
            help='Clear all sounds in the existing index before re-indexing all sounds. This option is normally not '
                 'needed as the command will clean any leftover sounds from the search index which are no longer'
                 'in the DB.')

        parser.add_argument(
            '--recreate-index',
            action='store_true',
            dest='recreate_index',
            default=False,
            help='Create a new index and index into it. Update the freesound alias to point to this new index.')


    def handle(self, *args, **options):
        # Get all indexed sound IDs and remove them
        clear_index = options['clear_index']
        if clear_index:
            delete_all_sounds_from_search_engine()

        base_url = "http://search:8983"

        recreate_index = options['recreate_index']
        schema_directory = os.path.join('.', "utils", "search", "schema")
        freesound_schema_definition = json.load(open(os.path.join(schema_directory, "freesound.json")))
        if recreate_index:
            current_date = datetime.datetime.now().strftime("%Y%m%d")
            collection_name = f"freesound_{current_date}"
            solrapi.create_collection_and_schema(collection_name, freesound_schema_definition, "username", base_url)

        # Get all sounds moderated and processed ok and add them to the search engine
        # Don't delete existing sounds in each loop because we clean up in the final step
        sounds_to_index_ids = list(
            Sound.objects.filter(processing_state="OK", moderation_state="OK").values_list('id', flat=True))
        console_logger.info("Re-indexing %d sounds to the search engine", len(sounds_to_index_ids))
        send_sounds_to_search_engine(sounds_to_index_ids, slice_size=options['size_size'], delete_if_existing=False, solr_collection_url=f"{base_url}/solr/{collection_name}")

        # Delete all sounds in the search engine which are not found in the DB. This part of code is to make sure that
        # no "leftover" sounds remain in the search engine, but should normally do nothing, specially if the
        # "clear_index" option is passed
        indexed_sound_ids = get_all_sound_ids_from_search_engine(solr_collection_url=f"{base_url}/solr/{collection_name}")
        sound_ids_to_delete = list(set(indexed_sound_ids).difference(sounds_to_index_ids))
        console_logger.info("Deleting %d non-existing sounds from the search engine", len(sound_ids_to_delete))
        if sound_ids_to_delete:
            delete_sounds_from_search_engine(sound_ids_to_delete, solr_collection_url=f"{base_url}/solr/{collection_name}")

        console_logger.info("Updating the freesound alias to point to the new index")
        solrapi.create_collection_alias(base_url, collection_name, "freesound")
