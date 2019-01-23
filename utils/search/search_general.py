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
from search import forms
from search.forms import SEARCH_SORT_OPTIONS_WEB
from utils.search.solr import Solr, SolrQuery, SolrResponseInterpreter, SolrException, \
    SolrResponseInterpreterPaginator
from utils.text import remove_control_chars

logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def search_prepare_sort(sort, options):
    """ for ordering by rating order by rating, then by number of ratings """
    if sort in [x[1] for x in options]:
        if sort == "avg_rating desc":
            sort = [sort, "num_ratings desc"]
        elif  sort == "avg_rating asc":
            sort = [sort, "num_ratings asc"]
        else:
            sort = [sort]
    else:
        sort = [forms.SEARCH_DEFAULT_SORT]
    return sort


def search_process_filter(filter_query):
    # Process the filter to replace humnan-readable Audio Commons descriptor names for the dynamic field names used in
    # Solr (e.g. ac_tonality -> ac_tonality_s, ac_tempo -> ac_tempo_i). The dynamic field names we define in Solr
    # schema are '*_b' (for bool), '*_d' (for float), '*_i' (for integer) and '*_s' (for string). At indexing time
    # we append these suffixes to the ac descirptor names so Solr can treat the types properly. Now we automatically
    # append the suffices to the filter names so users do not need to deal with that.
    for name, t in settings.AUDIOCOMMONS_INCLUDED_DESCRIPTOR_NAMES_TYPES:
        filter_query = filter_query.replace('ac_{0}:'.format(name), 'ac_{0}{1}:'
                                            .format(name, settings.SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[t]))
    return filter_query


def search_prepare_query(search_query,
                         filter_query,
                         sort,
                         current_page,
                         sounds_per_page,
                         id_weight=settings.DEFAULT_SEARCH_WEIGHTS['id'],
                         tag_weight=settings.DEFAULT_SEARCH_WEIGHTS['tag'],
                         description_weight=settings.DEFAULT_SEARCH_WEIGHTS['description'],
                         username_weight=settings.DEFAULT_SEARCH_WEIGHTS['username'],
                         pack_tokenized_weight=settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized'],
                         original_filename_weight=settings.DEFAULT_SEARCH_WEIGHTS['original_filename'],
                         grouping=False,
                         include_facets=True,
                         grouping_pack_limit=1,
                         offset=None,
                         in_ids=[]):
    query = SolrQuery()

    # Set field weights and scoring function
    field_weights = []
    if id_weight != 0:
        field_weights.append(("id", id_weight))
    if tag_weight != 0:
        field_weights.append(("tag", tag_weight))
    if description_weight != 0:
        field_weights.append(("description", description_weight))
    if username_weight != 0:
        field_weights.append(("username", username_weight))
    if pack_tokenized_weight != 0:
        field_weights.append(("pack_tokenized", pack_tokenized_weight))
    if original_filename_weight != 0:
        field_weights.append(("original_filename", original_filename_weight))
    query.set_dismax_query(search_query,
                           query_fields=field_weights,)

    # Set start and rows parameters (offset and size)
    if not offset:
        start = (current_page - 1) * sounds_per_page
    else:
        start = offset

    # Process filter
    filter_query = search_process_filter(filter_query)

    # Process filter for clustering
    if in_ids:
        filter_query += ' OR id:'.join(in_ids)

    # Set all options
    query.set_query_options(start=start, rows=sounds_per_page, field_list=["id"], filter_query=filter_query, sort=sort)

    # Specify query factes
    if include_facets:
        query.add_facet_fields("samplerate", "grouping_pack", "username", "tag", "bitrate", "bitdepth", "type", "channels", "license")
        query.set_facet_options_default(limit=5, sort=True, mincount=1, count_missing=False)
        query.set_facet_options("type", limit=len(sounds.models.Sound.SOUND_TYPE_CHOICES))
        query.set_facet_options("tag", limit=30)
        query.set_facet_options("username", limit=30)
        query.set_facet_options("grouping_pack", limit=10)
        query.set_facet_options("license", limit=10)

    # Add groups
    if grouping:
        query.set_group_field(group_field="grouping_pack")
        query.set_group_options(
            group_func=None,
            group_query=None,
            group_rows=10,
            group_start=0,
            group_limit=grouping_pack_limit,  # This is the number of documents that will be returned for each group. By default only 1 is returned.
            group_offset=0,
            group_sort=None,
            group_sort_ingroup=None,
            group_format='grouped',
            group_main=False,
            group_num_groups=True,
            group_cache_percent=0)
    return query


def perform_solr_query(q, current_page):
    """
    This util function performs the query to SOLR and returns needed parameters to continue with the view.
    The main reason to have this util function is to facilitate mocking in unit tests for this view.
    """
    solr = Solr(settings.SOLR_URL)
    results = SolrResponseInterpreter(solr.select(unicode(q)))
    paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
    page = paginator.page(current_page)
    return results.non_grouped_number_of_matches, results.facets, paginator, page, results.docs


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
    logger.info("Adding %d sounds to solr index" % len(documents))
    solr.add(documents)


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
    logger.info("deleting sound with id %d" % sound_id)
    try:
        Solr(settings.SOLR_URL).delete_by_id(sound_id)
    except (SolrException, socket.error) as e:
        logger.error('could not delete sound with id %s (%s).' % (sound_id, e))


def delete_sounds_from_solr(sound_ids):
    solr_max_boolean_clause = 1000  # This number is specified in solrconfig.xml
    for count, i in enumerate(range(0, len(sound_ids), solr_max_boolean_clause)):
        range_ids = sound_ids[i:i+solr_max_boolean_clause]
        try:
            logger.info("deleting %i sounds from solr [%i of %i, %i sounds]" %
                        (len(sound_ids), count + 1, int(math.ceil(float(len(sound_ids)) / solr_max_boolean_clause)),
                         len(range_ids)))
            sound_ids_query = ' OR '.join(['id:{0}'.format(sid) for sid in range_ids])
            Solr(settings.SOLR_URL).delete_by_query(sound_ids_query)
        except (SolrException, socket.error) as e:
            logger.error('could not delete solr sounds chunk %i of %i' %
                         (count + 1, int(math.ceil(float(len(sound_ids)) / solr_max_boolean_clause))))
