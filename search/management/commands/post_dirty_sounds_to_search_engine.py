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

import datetime
import logging
import time

from django.conf import settings
from django.core.cache import cache

from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand
from utils.search import get_search_engine
from utils.search.search_sounds import add_sounds_to_search_engine, send_update_similarity_vectors_in_search_engine, delete_sounds_from_search_engine

console_logger = logging.getLogger("console")


def time_stats(done, total, starttime):
    nowtime = time.monotonic()
    position = done*1.0 / total
    duration = round(nowtime - starttime)
    durdelta = datetime.timedelta(seconds=duration)
    remaining = round((duration / position) - duration) if position > 0 else 0
    remdelta = datetime.timedelta(seconds=remaining)

    return str(durdelta), str(remdelta)


def send_sounds_to_search_engine(sounds_to_index_ids, slice_size=4000, delete_if_existing=False, include_similarity_vectors=False, solr_collection_url=None, update=False):
    total_sounds = len(sounds_to_index_ids)
    console_logger.info(f"Starting to post dirty sounds to solr. {total_sounds} sounds to be added/updated to the search engine")
    n_sounds_indexed_correctly = 0
    starttime = time.monotonic()
    for i in range(0, total_sounds, slice_size):
        sound_ids_slice = sounds_to_index_ids[i:i + slice_size]
        if delete_if_existing:
            delete_sounds_from_search_engine(sound_ids_slice, solr_collection_url=solr_collection_url)
        sound_objects = Sound.objects.bulk_query_solr(sound_ids_slice)
        n_sounds_indexed = add_sounds_to_search_engine(sound_objects, update=update, include_similarity_vectors=include_similarity_vectors, solr_collection_url=solr_collection_url)
        if n_sounds_indexed > 0:
            Sound.objects.filter(pk__in=sound_ids_slice).update(is_index_dirty=False)
        n_sounds_indexed_correctly += n_sounds_indexed
        elapsed, remaining = time_stats(n_sounds_indexed_correctly, total_sounds, starttime)
        console_logger.info(f"Added {n_sounds_indexed_correctly}/{total_sounds} sounds. Elapsed: {elapsed}, Remaining: {remaining}")

        # Clear empty query cache as we have modified the sounds index
        cache.delete(settings.SEARCH_EMPTY_QUERY_CACHE_KEY, None)

    return n_sounds_indexed_correctly


def update_similarity_vectors_in_search_engine(sounds_to_index_ids, slice_size=4000, solr_collection_url=None):
    total_sounds = len(sounds_to_index_ids)
    console_logger.info(f"Starting to update similarity vectors in solr. {total_sounds} sounds to be updated")
    n_sounds_indexed_correctly = 0
    starttime = time.monotonic()
    for i in range(0, total_sounds, slice_size):
        sound_ids_slice = sounds_to_index_ids[i:i + slice_size]
        sound_objects = Sound.objects.bulk_query_solr(sound_ids_slice)
        n_sounds_indexed = send_update_similarity_vectors_in_search_engine(sound_objects, solr_collection_url=solr_collection_url)
        n_sounds_indexed_correctly += n_sounds_indexed
        elapsed, remaining = time_stats(n_sounds_indexed_correctly, total_sounds, starttime)
        console_logger.info(f"Updated {n_sounds_indexed_correctly}/{total_sounds} sounds. Elapsed: {elapsed}, Remaining: {remaining}")


class Command(LoggingBaseCommand):
    help = 'Add all sounds with is_index_dirty flag True to the search engine'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slize_size',
            dest='size_size',
            default=500,
            type=int,
            help='How many posts to add at once')

        parser.add_argument(
            '-d', '--delete_if_existing',
            action='store_true',
            dest='delete_if_existing',
            default=False,
            help='Using the option --delete_if_existing, sounds already existing in the search engine will be removed'
                 ' before (re-)indexing.')

    def handle(self, *args, **options):
        self.log_start()

        # Index all those which are processed and moderated ok that has is_index_dirty
        sounds_to_index_ids = list(Sound.objects
                                   .filter(processing_state="OK", moderation_state="OK", is_index_dirty=True)
                                   .values_list('id', flat=True))
        n_sounds_indexed_correctly = send_sounds_to_search_engine(
            sounds_to_index_ids, slice_size=options['size_size'], delete_if_existing=options['delete_if_existing'], include_similarity_vectors=True, update=True)

        # Find all the index dirty sounds which are not processed/moderated ok and therefore should not be in the
        # search index, and trigger the deletion of these sounds in the index so that they disappear if they were
        # present. This bit of code should ideally be redundant as sounds should be deleted from the index when they
        # are deleted from the database or when their moderation state changes, etc. But in case for some reason there
        # are leftovers in the index, we delete them here.
        sounds_dirty_to_remove = \
            Sound.objects.filter(is_index_dirty=True).exclude(moderation_state='OK', processing_state='OK')
        n_deleted_sounds = 0
        search_engine = get_search_engine()
        for sound in sounds_dirty_to_remove:
            if search_engine.sound_exists_in_index(sound):
                # We need to know if the sound exists in solr so that besides deleting it (which could be accomplished
                # by simply using delete_sounds_from_solr), we know whether we have to change is_index_dirty state. If
                # we do not change it, then we would try to delete the sound at every attempt.
                delete_sounds_from_search_engine([sound.id])
                n_deleted_sounds += 1
                sound.is_index_dirty = False
                sound.save()

        self.log_end({'n_sounds_added': n_sounds_indexed_correctly, 'n_sounds_deleted': n_deleted_sounds})
