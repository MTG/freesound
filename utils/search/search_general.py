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
import socket
import time

from django.conf import settings

import sounds
from search.forms import SEARCH_SORT_OPTIONS_WEB
from search.views import search_prepare_sort, search_prepare_query
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, SolrException
from utils.text import remove_control_chars

logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def convert_to_solr_document(sound):
    # logger.info("creating solr XML from sound %d" % sound.id)
    document = dict()
    document["id"] = sound.id
    document["username"] = sound.user.username
    document["created"] = sound.created
    document["original_filename"] = remove_control_chars(sound.original_filename)
    document["description"] = remove_control_chars(sound.description)
    document["tag"] = list(sound.tags.select_related("tag").values_list('tag__name', flat=True))
    document["license"] = sound.license.name
    document["is_explicit"] = sound.is_explicit
    document["is_remix"] = bool(sound.sources.count())
    document["was_remixed"] = bool(sound.remixes.count())
    if sound.pack:
        document["pack"] = remove_control_chars(sound.pack.name)
        document["grouping_pack"] = str(sound.pack.id) + "_" + remove_control_chars(sound.pack.name)
    else:
        document["grouping_pack"] = str(sound.id)
    document["is_geotagged"] = sound.geotag_id is not None
    if sound.geotag_id is not None:
        if not math.isnan(sound.geotag.lon) and not math.isnan(sound.geotag.lat):
            document["geotag"] = str(sound.geotag.lon) + " " + str(sound.geotag.lat)
    document["type"] = sound.type
    document["duration"] = sound.duration
    document["bitdepth"] = sound.bitdepth if sound.bitdepth != None else 0
    document["bitrate"] = sound.bitrate if sound.bitrate != None else 0
    document["samplerate"] = int(sound.samplerate)
    document["filesize"] = sound.filesize
    document["channels"] = sound.channels
    document["md5"] = sound.md5
    document["num_downloads"] = sound.num_downloads
    document["avg_rating"] = sound.avg_rating
    document["num_ratings"] = sound.num_ratings
    document["comment"] = [remove_control_chars(comment_text) for comment_text in
                           sound.comments.values_list('comment', flat=True)]
    document["comments"] = sound.num_comments
    document["waveform_path_m"] = sound.locations()["display"]["wave"]["M"]["path"]
    document["waveform_path_l"] = sound.locations()["display"]["wave"]["L"]["path"]
    document["spectral_path_m"] = sound.locations()["display"]["spectral"]["M"]["path"]
    document["spectral_path_l"] = sound.locations()["display"]["spectral"]["L"]["path"]
    document["preview_path"] = sound.locations()["preview"]["LQ"]["mp3"]["path"]
    return document


def add_sounds_to_solr(sounds):
    console_logger.info("adding multiple sounds to solr index")
    solr = Solr(settings.SOLR_URL)
    console_logger.info("creating XML")
    documents = map(convert_to_solr_document, sounds)
    console_logger.info("posting to Solr")
    solr.add(documents)


def add_all_sounds_to_solr(sound_queryset, slice_size=4000, mark_index_clean=False):
    # Pass in a queryset to avoid needing a reference to
    # the Sound class, it causes circular imports.
    num_sounds = sound_queryset.count()
    num_correctly_indexed_sounds = 0
    for i in range(0, num_sounds, slice_size):
        console_logger.info("Adding %i sounds to solr, slice %i", slice_size, i)
        try:
            sounds_to_update = sound_queryset[i:i+slice_size]
            add_sounds_to_solr(sounds_to_update)
            if mark_index_clean:
                console_logger.info("Marking sounds as clean.")
                sounds.models.Sound.objects.filter(pk__in=[snd.id for snd in sounds_to_update])\
                    .update(is_index_dirty=False)
                num_correctly_indexed_sounds += len(sounds_to_update)
        except SolrException as e:
            console_logger.error("failed to add sound batch to solr index, reason: %s", str(e))
            raise
    return num_correctly_indexed_sounds


def get_all_sound_ids_from_solr(limit=False):
    logger.info("getting all sound ids from solr.")
    if not limit:
        limit = 99999999999999
    solr = Solr(settings.SOLR_URL)
    solr_ids = []
    solr_count = None
    PAGE_SIZE = 2000
    current_page = 1
    while (len(solr_ids) < solr_count or solr_count is None) and len(solr_ids) < limit:
        response = SolrResponseInterpreter(
            solr.select(unicode(search_prepare_query(
                '', '', search_prepare_sort('created asc', SEARCH_SORT_OPTIONS_WEB), current_page, PAGE_SIZE,
                include_facets=False))))
        solr_ids += [element['id'] for element in response.docs]
        solr_count = response.num_found
        current_page += 1
    return sorted(solr_ids)


def check_if_sound_exists_in_solr(sound):
    solr = Solr(settings.SOLR_URL)
    response = SolrResponseInterpreter(
        solr.select(unicode(search_prepare_query(
            '', 'id:%i' % sound.id, search_prepare_sort('created asc', SEARCH_SORT_OPTIONS_WEB), 1, 1))))
    return response.num_found > 0


def get_random_sound_from_solr():
    """ Get a random sound from solr.
    This is used for random sound browsing. We filter explicit sounds,
    but otherwise don't have any other restrictions on sound attributes
    """
    solr = Solr(settings.SOLR_URL)
    query = SolrQuery()
    sort = ['random_%d asc' % (time.time())]
    filter_query = 'is_explicit:0'
    query.set_query("*:*")
    query.set_query_options(start=0, rows=1, field_list=["*"], filter_query=filter_query, sort=sort)
    try:
        response = SolrResponseInterpreter(solr.select(unicode(query)))
        docs = response.docs
        if docs:
            return docs[0]
    except socket.error:
        pass
    return {}


def delete_sound_from_solr(sound_id):
    logger.info("deleting sound with id %d" % sound_id)
    try:
        Solr(settings.SOLR_URL).delete_by_id(sound_id)
    except (SolrException, socket.error) as e:
        logger.error('could not delete sound with id %s (%s).' % (sound_id, e))
