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
import random
import socket

from django.conf import settings

import sounds
from search.forms import SEARCH_SORT_OPTIONS_WEB
from search.views import search_prepare_sort, search_prepare_query
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, SolrException
from utils.text import remove_control_chars

search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def convert_to_solr_document(sound):
    document = {}

    # Basic sound fields
    keep_fields = ['username', 'created', 'is_explicit', 'avg_rating', 'is_remix', 'num_ratings', 'channels', 'md5',
                      'was_remixed', 'original_filename', 'duration', 'type', 'id', 'num_downloads', 'filesize']
    for key in keep_fields:
        document[key] = getattr(sound, key)
    document["original_filename"] = remove_control_chars(getattr(sound, "original_filename"))
    document["description"] = remove_control_chars(getattr(sound, "description"))
    document["tag"] = getattr(sound, "tag_array")
    document["license"] = getattr(sound, "license_name")

    if getattr(sound, "pack_id"):
        document["pack"] = remove_control_chars(getattr(sound, "pack_name"))
        document["grouping_pack"] = str(getattr(sound, "pack_id")) + "_" + remove_control_chars(getattr(sound, "pack_name"))
    else:
        document["grouping_pack"] = str(getattr(sound, "id"))

    document["is_geotagged"] = False
    if getattr(sound, "geotag_id"):
        document["is_geotagged"] = True
        if not math.isnan(getattr(sound, "geotag_lon")) and not math.isnan(getattr(sound, "geotag_lat")):
            document["geotag"] = str(getattr(sound, "geotag_lon")) + " " + str(getattr(sound, "geotag_lat"))

    document["bitdepth"] = getattr(sound, "bitdepth") if getattr(sound, "bitdepth") else 0
    document["bitrate"] = getattr(sound, "bitrate") if getattr(sound, "bitrate") else 0
    document["samplerate"] = int(getattr(sound, "samplerate")) if getattr(sound, "samplerate") else 0

    document["comment"] = [remove_control_chars(comment_text) for comment_text in getattr(sound, "comments_array")]
    document["comments"] = getattr(sound, "num_comments")
    locations = sound.locations()
    document["waveform_path_m"] = locations["display"]["wave"]["M"]["path"]
    document["waveform_path_l"] = locations["display"]["wave"]["L"]["path"]
    document["spectral_path_m"] = locations["display"]["spectral"]["M"]["path"]
    document["spectral_path_l"] = locations["display"]["spectral"]["L"]["path"]
    document["preview_path"] = locations["preview"]["LQ"]["mp3"]["path"]

    # Audio Commons analysis
    # NOTE: as the sound object here is the one returned by SoundManager.bulk_query_solr, it will have the Audio Commons
    # descriptor fields under a property called 'ac_analysis'.
    ac_analysis = getattr(sound, "ac_analysis")
    if ac_analysis is not None:
        # If analysis is present, index all existing analysis fields under Solr's dynamic fields "*_i", "*_d", "*_s"
        # and "*_b" depending on the value's type. Also add Audio Commons prefix.
        for key, value in ac_analysis.items():
            suffix = settings.SOLR_DYNAMIC_FIELDS_SUFFIX_MAP.get(type(value), None)
            if suffix:
                document['{0}{1}{2}'.format(settings.AUDIOCOMMONS_DESCRIPTOR_PREFIX, key, suffix)] = value

    return document


def add_sounds_to_solr(sounds):
    solr = Solr(settings.SOLR_URL)
    documents = [convert_to_solr_document(s) for s in sounds]
    console_logger.info("Adding %d sounds to solr index" % len(documents))
    search_logger.info("Adding %d sounds to solr index" % len(documents))
    solr.add(documents)


def commit():
    solr = Solr(settings.SOLR_URL)
    solr.commit()


def add_all_sounds_to_solr(sound_queryset, slice_size=1000, mark_index_clean=False, delete_if_existing=False):
    """
    Add all sounds from the sound_queryset to the Solr index.
    :param QuerySet sound_queryset: queryset of Sound objects.
    :param int slice_size: sounds are indexed iteratively in chunks of this size.
    :param bool mark_index_clean: if True, set 'is_index_dirty=False' for the indexed sounds' objects.
    :param bool delete_if_existing: if True, delete sounds from Solr index before (re-)indexing them. This is used
    because our sounds include dynamic fields which otherwise might not be properly updated when adding a sound that
    already exists in the Solr index.
    :return int: number of correctly indexed sounds
    """
    num_correctly_indexed_sounds = 0
    all_sound_ids = sound_queryset.values_list('id', flat=True).all()
    n_slices = int(math.ceil(float(len(all_sound_ids))/slice_size))
    for i in range(0, len(all_sound_ids), slice_size):
        console_logger.info("Adding sounds to solr, slice %i of %i", (i/slice_size) + 1, n_slices)
        try:
            sound_ids = all_sound_ids[i:i+slice_size]
            sounds_qs = sounds.models.Sound.objects.bulk_query_solr(sound_ids)
            if delete_if_existing:
                delete_sounds_from_solr(sound_ids=sound_ids)
            add_sounds_to_solr(sounds_qs)

            if mark_index_clean:
                console_logger.info("Marking sounds as clean.")
                sounds.models.Sound.objects.filter(pk__in=sound_ids).update(is_index_dirty=False)
            num_correctly_indexed_sounds += len(sound_ids)
        except SolrException as e:
            console_logger.error("failed to add sound batch to solr index, reason: %s", str(e))
            raise
    commit()
    return num_correctly_indexed_sounds


def get_all_sound_ids_from_solr(limit=False):
    search_logger.info("getting all sound ids from solr.")
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
    rand_key = random.randint(1, 10000000)
    sort = ['random_%d asc' % rand_key]
    filter_query = 'is_explicit:0'
    query.set_query("*:*")
    query.set_query_options(start=0, rows=1, field_list=["*"], filter_query=filter_query, sort=sort)
    try:
        response = SolrResponseInterpreter(solr.select(unicode(query)))
        docs = response.docs
        if docs:
            return docs[0]
    except (SolrException, socket.error):
        pass
    return {}


def delete_sound_from_solr(sound_id):
    search_logger.info("deleting sound with id %d" % sound_id)
    try:
        Solr(settings.SOLR_URL).delete_by_id(sound_id)
    except (SolrException, socket.error) as e:
        search_logger.error('could not delete sound with id %s (%s).' % (sound_id, e))


def delete_sounds_from_solr(sound_ids):
    solr_max_boolean_clause = 1000  # This number is specified in solrconfig.xml
    for count, i in enumerate(range(0, len(sound_ids), solr_max_boolean_clause)):
        range_ids = sound_ids[i:i+solr_max_boolean_clause]
        try:
            search_logger.info(
                "deleting %i sounds from solr [%i of %i, %i sounds]" %
                (len(sound_ids),
                 count + 1,
                 int(math.ceil(float(len(sound_ids)) / solr_max_boolean_clause)),
                 len(range_ids)))
            sound_ids_query = ' OR '.join(['id:{0}'.format(sid) for sid in range_ids])
            Solr(settings.SOLR_URL).delete_by_query(sound_ids_query)
        except (SolrException, socket.error) as e:
            search_logger.error('could not delete solr sounds chunk %i of %i' %
                                (count + 1, int(math.ceil(float(len(sound_ids)) / solr_max_boolean_clause))))
