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
from utils.search.solr import Solr, SolrException
from utils.text import remove_control_chars
from sounds.models import Sound

console_logger = logging.getLogger("console")

def convert_to_solr_document(sound_obj):
    document = {}
    sound = sound_obj.__dict__
    keep_fields = ['username', 'created', 'is_explicit', 'avg_rating', 'is_remix', 'num_ratings', 'channels',
            'was_remixed', 'original_filename', 'duration', 'type', 'id', 'num_downloads', 'filesize']
    for key in keep_fields:
        document[key] = sound[key]
    document["original_filename"] = remove_control_chars(sound["original_filename"])
    document["description"] = remove_control_chars(sound["description"])
    document["tag"] = sound["tag_array"]
    document["license"] = sound["license_name"]

    if "pack_id" in sound:
        document["pack"] = remove_control_chars(sound["pack_name"])
        document["grouping_pack"] = str(sound["pack_id"]) + "_" + remove_control_chars(sound["pack_name"])
    else:
        document["grouping_pack"] = str(sound["id"])

    document["is_geotagged"] = False
    if "geotag_id" in sound:
        sound["is_geotagged"] = True
        if not math.isnan(sound["geotag_lon"]) and not math.isnan(sound["geotag_lat"]):
            document["geotag"] = str(sound["geotag_lon"]) + " " + str(sound["geotag_lat"])

    document["bitdepth"] = sound["bitdepth"] if "bitdepth" in sound else 0
    document["bitrate"] = sound["bitrate"] if "bitrate" in sound else 0
    document["samplerate"] = int(sound["samplerate"]) if "samplerate" in sound else 0

    document["comment"] = [remove_control_chars(comment_text) for comment_text in sound["comments_array"]]
    document["comments"] = sound["num_comments"]
    locations = sound_obj.locations()
    document["waveform_path_m"] = locations["display"]["wave"]["M"]["path"]
    document["waveform_path_l"] = locations["display"]["wave"]["L"]["path"]
    document["spectral_path_m"] = locations["display"]["spectral"]["M"]["path"]
    document["spectral_path_l"] = locations["display"]["spectral"]["L"]["path"]
    document["preview_path"] = locations["preview"]["LQ"]["mp3"]["path"]
    return document


def add_sounds_to_solr(sounds):
    console_logger.info("adding multiple sounds to solr index")
    solr = Solr(settings.SOLR_URL)
    console_logger.info("creating XML")
    documents = map(convert_to_solr_document, sounds)
    console_logger.info("posting to Solr")
    solr.add(documents)


class Command(BaseCommand):
    args = ''
    help = 'Take all sounds and send them to Solr'

    def handle(self, *args, **options):
        slice_size = 4000
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
