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
from utils.search.search_general import add_all_sounds_to_solr, delete_sound_from_solr, check_if_sound_exists_in_solr
from utils.search.solr import SolrException

logger = logging.getLogger("web")
console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = 'Add all sounds with is_index_dirty flag True to SOLR index'

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--delete-if-existing',
            action='store_true',
            dest='delete-if-existing',
            default=False,
            help='Using the option --delete-if-existing, sounds already existing in the SOLR index will be removed'
                 ' before (re-)indexing.')

    def handle(self, *args, **options):

        # Index all those which are processed and moderated ok that has is_index_dirty
        sounds_to_index = Sound.objects.filter(processing_state="OK", moderation_state="OK", is_index_dirty=True)
        num_sounds = sounds_to_index.count()
        logger.info("Starting posting dirty sounds to solr. %i sounds to be added/updated to the solr index"
                    % num_sounds)

        num_correctly_indexed_sounds = add_all_sounds_to_solr(
            sounds_to_index, mark_index_clean=True, delete_if_existing=options['delete-if-existing'])

        logger.info("Finished posting dirty sounds to solr. %i sounds have been added/updated"
                    % num_correctly_indexed_sounds)

        # Remove all those which are not processed or moderated ok and that are still in solr (should not happen)
        sounds_dirty_to_remove = \
            Sound.objects.filter(is_index_dirty=True).exclude(moderation_state='OK', processing_state='OK')
        n_deleted_sounds = 0
        for sound in sounds_dirty_to_remove:
            if check_if_sound_exists_in_solr(sound):
                # We need to know if the sound exists in solr so that besides deleting it (which could be accomplished
                # by simply using delete_sound_from_solr), we know whether we have to change is_index_dirty state. If
                # we do not change it, then we would try to delete the sound at every attempt.
                delete_sound_from_solr(sound.id)
                n_deleted_sounds += 1
                sound.is_index_dirty = False
                sound.save()
        logger.info("Deleted %i sounds from solr index." % n_deleted_sounds)
