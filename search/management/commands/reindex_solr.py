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
import math

from django.conf import settings
from django.core.management.base import BaseCommand
from utils.search.solr import SolrException
from utils.text import remove_control_chars
from utils.search.search_general import delete_sound_from_solr, add_sounds_to_solr
from sounds.models import Sound

console_logger = logging.getLogger("console")

class Command(BaseCommand):
    args = ''
    help = 'Take all sounds and send them to Solr'

    def handle(self, *args, **options):
        slice_size = 1000
        num_sounds = Sound.objects.filter(processing_state="OK", moderation_state="OK").count()
        for i in range(0, num_sounds, slice_size):
            console_logger.info("Adding %i sounds to solr, slice %i", slice_size, i)
            try:
                # Get all sounds moderated and processed ok
                where = "sound.moderation_state = 'OK' AND sound.processing_state = 'OK' AND sound.id > %s"
                order_by = "sound.id ASC"
                sounds_qs = Sound.objects.bulk_query_solr(where, order_by, slice_size, (i, ))
                add_sounds_to_solr(sounds_qs)
            except SolrException as e:
                console_logger.error("failed to add sound batch to solr index, reason: %s", str(e))
                raise

        # Get all sounds that should not be in solr and remove them if they are
        sound_qs = Sound.objects.exclude(processing_state="OK", moderation_state="OK")
        for sound in sound_qs:
            delete_sound_from_solr(sound.id)  # Will only do something if sound in fact exists in solr
