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
import json

import re
from django.conf import settings
from django.utils.http import urlquote_plus
from pyparsing import ParseException

import sounds
from search import forms
from search.forms import SEARCH_SORT_OPTIONS_WEB
from utils.logging_filters import get_client_ip
from utils.search.lucene_parser import parse_query_filter_string
from utils.search.backend.pysolr.wrapper import SearchEngine, QueryManager, SearchEngineException, convert_to_search_engine_document

search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def search_prepare_sort(sort, options):
    """Creates sort list for ordering by rating.

    Order by rating, then by number of ratings.
    
    Args:
        sort (str): sort url query parameter.
        options (List[Tuple(str)]): list containing 2-element tuples with the ordering option names
        and their corresponding fields in the database. 

    Returns:
        List[str]: list containing the sorting parameters.
    """
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
    """Process the filter to replace humnan-readable Audio Commons descriptor names.

    Used for the dynamic field names used in Solr (e.g. ac_tonality -> ac_tonality_s, ac_tempo -> ac_tempo_i).
    The dynamic field names we define in Solr schema are '*_b' (for bool), '*_d' (for float), '*_i' (for integer) 
    and '*_s' (for string). At indexing time we append these suffixes to the ac descirptor names so Solr can 
    treat the types properly. Now we automatically append the suffices to the filter names so users do not 
    need to deal with that.

    Args:
        filter_query (str): query filter string.

    Returns:
        str: processed filter query string.
    """
    for name, t in settings.AUDIOCOMMONS_INCLUDED_DESCRIPTOR_NAMES_TYPES:
        filter_query = filter_query.replace('ac_{0}:'.format(name), 'ac_{0}{1}:'
                                            .format(name, settings.SOLR_DYNAMIC_FIELDS_SUFFIX_MAP[t]))
    return filter_query


def split_filter_query(filter_query, parsed_filters, cluster_id):
    """Pre-process parsed search filter parameters and returns the filters' information.

    This function is used in the search template to display the filter and the link when removing them.
    The cluster ID is provided seprated from the parsed filters in order to keep clustering explicitly 
    separated from the rest of the filters.

    Args:
        filter_query (str): query filter string.
        parsed_filters (List[List[str]]): parsed query filter.
        cluster_id (str): cluster filter string.

    Returns:
        List[dict]: list of dictionaries containing the filter name and the url when removing the filter.
    """
    # Generate array with information of filters
    filter_query_split = []
    if parsed_filters:
        for filter_list_str in parsed_filters:
            # filter_list_str is a list of str ['<filter_name>', ':', '"', '<filter_value>', '"']
            filter_name = filter_list_str[0]
            if filter_name != "duration" and filter_name != "is_geotagged":
                valid_filter = True
                filter_str = ''.join(filter_list_str)
                filter_display = ''.join(filter_list_str).replace('"', '')
                if filter_name == "grouping_pack":
                    filter_value = filter_list_str[-1].rstrip('"')
                    # If pack does not contain "_" then it's not a valid pack filter
                    if "_" in filter_value:
                        filter_display = "pack:"+ ''.join(filter_value.split("_")[1:])
                    else:
                        valid_filter = False
                
                if valid_filter:
                    filter = {
                        'name': filter_display,
                        'remove_url': urlquote_plus(filter_query.replace(filter_str, '')),
                        'cluster_id': cluster_id,
                    }
                    filter_query_split.append(filter)

    # add cluster filter information
    if settings.ENABLE_SEARCH_RESULTS_CLUSTERING:
        if cluster_id and cluster_id.isdigit():
            filter_query_split.append({
                'name': "Cluster #" + cluster_id,
                'remove_url': urlquote_plus(filter_query),
                'cluster_id': '',
            })

    return filter_query_split


def search_prepare_parameters(request):
    """Parses and pre-process search input parameters from the request object and returns them as a dict.

    From the request object, it constructs all the parameters needed for building the Solr query 
    object. Additionally, other variables are returned for logging purpose, and for building the search
    view context variables.

    This functions also make easier the replication of the Solr query from the clustering engine.

    Args:
        request (HttpRequest): request associated with the search query submited by the user.
    
    Returns:
        Tuple(dict, dict, dict): 3-element tuple containing the query parameters needed for building the Solr 
        query, the advanced search params to be logged and some extra parameters needed in the search view. 
    """
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "").strip().lstrip()
    cluster_id = request.GET.get('cluster_id', "")

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    sort_unformatted = request.GET.get("s", None)
    
    # If the query is filtered by pack, do not collapse sounds of the same pack (makes no sense)
    # If the query is through AJAX (for sources remix editing), do not collapse
    grouping = request.GET.get("g", "1")  # Group by default
    if "pack" in filter_query or request.GET.get("ajax", "") == "1":
        grouping = False

    # If the query is filtered by pack, do not add the "only sounds with pack" filter (makes no sense)
    only_sounds_with_pack = request.GET.get("only_p", "0") == "1"  # By default, do not limit to sounds with pack
    if "pack" in filter_query:
        only_sounds_with_pack = False

    # Set default values
    id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id']
    tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag']
    description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description']
    username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username']
    pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
    original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename']

    # Parse advanced search options
    advanced = request.GET.get("advanced", "")
    advanced_search_params_dict = {}

    if advanced == "1":
        a_tag = request.GET.get("a_tag", "")
        a_filename = request.GET.get("a_filename", "")
        a_description = request.GET.get("a_description", "")
        a_packname = request.GET.get("a_packname", "")
        a_soundid = request.GET.get("a_soundid", "")
        a_username = request.GET.get("a_username", "")

        # These are stored in a dict to facilitate logging and passing to template
        advanced_search_params_dict.update({
            'a_tag': a_tag,
            'a_filename': a_filename,
            'a_description': a_description,
            'a_packname': a_packname,
            'a_soundid': a_soundid,
            'a_username': a_username,
        })

        # If none is selected use all (so other filter can be appleid)
        if a_tag or a_filename or a_description or a_packname or a_soundid or a_username != "" :

            # Initialize all weights to 0
            id_weight = 0
            tag_weight = 0
            description_weight = 0
            username_weight = 0
            pack_tokenized_weight = 0
            original_filename_weight = 0

            # Set the weights of selected checkboxes
            if a_soundid != "":
                id_weight = settings.DEFAULT_SEARCH_WEIGHTS['id']
            if a_tag != "":
                tag_weight = settings.DEFAULT_SEARCH_WEIGHTS['tag']
            if a_description != "":
                description_weight = settings.DEFAULT_SEARCH_WEIGHTS['description']
            if a_username != "":
                username_weight = settings.DEFAULT_SEARCH_WEIGHTS['username']
            if a_packname != "":
                pack_tokenized_weight = settings.DEFAULT_SEARCH_WEIGHTS['pack_tokenized']
            if a_filename != "":
                original_filename_weight = settings.DEFAULT_SEARCH_WEIGHTS['original_filename']

    sort_options = SEARCH_SORT_OPTIONS_WEB
    sort = search_prepare_sort(sort_unformatted, sort_options)

    # parse query filter string and remove empty value fields
    parsing_error = False
    try:
        parsed_filters = parse_query_filter_string(filter_query)
    except ParseException as e:
        parsed_filters = []
        parsing_error = True

    filter_query = ' '.join([''.join(filter_str) for filter_str in parsed_filters])

    filter_query_non_facets, has_facet_filter = remove_facet_filters(parsed_filters)

    query_params = {
        'search_query': search_query,
        'filter_query': filter_query,
        'sort': sort,
        'current_page': current_page,
        'sounds_per_page': settings.SOUNDS_PER_PAGE,
        'id_weight': id_weight,
        'tag_weight': tag_weight,
        'description_weight': description_weight,
        'username_weight': username_weight,
        'pack_tokenized_weight': pack_tokenized_weight,
        'original_filename_weight': original_filename_weight,
        'grouping': grouping,
        'only_sounds_with_pack': only_sounds_with_pack,
    }

    filter_query_link_more_when_grouping_packs = filter_query.replace(' ','+')


    # These variables are not used for querying the sound collection
    # We keep them separated in order to facilitate the distinction between variables used for performing
    # the Solr query and these extra ones needed for rendering the search template page
    extra_vars = {
        'filter_query_link_more_when_grouping_packs': filter_query_link_more_when_grouping_packs,
        'sort_unformatted': sort_unformatted,
        'advanced': advanced,
        'sort_options': sort_options,
        'cluster_id': cluster_id,
        'filter_query_non_facets': filter_query_non_facets,
        'has_facet_filter': has_facet_filter,
        'parsed_filters': parsed_filters,
        'parsing_error': parsing_error
    }

    return query_params, advanced_search_params_dict, extra_vars


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
                         only_sounds_with_pack=False,
                         in_ids=[]):
    """Create the Solr query object given the query parameters.
    
    Args:
        search_query (str): query string.
        filter_query (str): query filter string.
        sort (str): sort option string.
        current_page (int): requested page of the results.
        sounds_per_page (int): number of sounds per page.
        id_weight (int): id weight for the query.
        tag_weight (int): tag weight for the query.
        description_weight (int): description weight for the query.
        username_weight (int): username weight for the query.
        pack_tokenized_weight (int): pack weight for the query.
        original_filename_weight (int): filename weight for the query.
        grouping (bool): only show one (or more) sounds for each pack.
        include_facets (bool): include facets or no.
        grouping_pack_limit (int): number of sounds showed for each pack.
        offset (int): a numerical offset.
        only_sounds_with_pack (bool): include only sound from pack or no.
        in_ids (list): list of sound ids for cluster filter facet.

    Returns: (QueryManager): the query object corresponding to the user submitted query.

    """
    query = QueryManager()

    # Set field weights and scoring function
    field_weights = []
    for weight, weight_str in [(id_weight, "id"),
                               (tag_weight, "tag"),
                               (description_weight, "description"), 
                               (username_weight, "username"),
                               (pack_tokenized_weight, "pack_tokenized"),
                               (original_filename_weight, "original_filename")]:
        if weight != 0:
            field_weights.append((weight_str, weight))

    query.set_dismax_query(search_query,
                           query_fields=field_weights,)

    # Set start and rows parameters (offset and size)
    if not offset:
        start = (current_page - 1) * sounds_per_page
    else:
        start = offset

    # Process filter
    filter_query = search_process_filter(filter_query)
    if only_sounds_with_pack and not 'pack:' in filter_query:
        filter_query += ' pack:*'  # Add a filter so that only sounds with packs are returned

    # Process filter for clustering.
    # When applying clustering facet, a in_ids argument is passed. We check if fliters exsit and in this case 
    # add a AND rule with the ids in order to combine facet and cluster facets. If no filter exist, we just 
    # add the filter by id.
    if in_ids:
        if filter_query:
            if len(in_ids) == 1:
                filter_query += ' AND id:{}'.format(in_ids[0])
            else:
                filter_query += ' AND (id:'
                filter_query += ' OR id:'.join(in_ids)
                filter_query += ')'
        else:
            if len(in_ids) == 1:
                filter_query += 'id:{}'.format(in_ids[0])
            else:
                filter_query += 'id:'
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


def remove_facet_filters(parsed_filters):
    """Process query filter string to keep only non facet filters

    Fact filters correspond to the filters that can be applied using one of the displayed facet in
    the search interface. It is useful for being able to combine classic facet filters and clustering
    because clustering has to be done on the results of a search without applying facet filters (we want
    to have the clustering facet behaving as a traditional facet, meaning that the clustering should not 
    be re-triggered when applying new facet filters on the results).
    Addtionaly, it returns a boolean that indicates if a facet filter was present in the query.

    Args:
        parsed_filters (List[List[str]]): parsed query filter.
    
    Returns: 
        filter_query (str): query filter string with only non facet filters.
        has_facet_filter (bool): boolean indicating if there exist facet filters in the processed string.
    """
    facet_filter_strings = (
        "samplerate", 
        "grouping_pack", 
        "username", 
        "tag", 
        "bitrate", 
        "bitdepth", 
        "type", 
        "channels", 
        "license",
    )
    has_facet_filter = False
    filter_query = ""

    if parsed_filters:       
        filter_query_parts = []
        for parsed_filter in parsed_filters:
            if parsed_filter[0] in facet_filter_strings:
                has_facet_filter = True 
            else:
                filter_query_parts.append(''.join(parsed_filter))

        filter_query = ' '.join(filter_query_parts)
    
    return filter_query, has_facet_filter


def perform_solr_query(q, current_page):
    """
    This util function performs the query to Solr and returns needed parameters to continue with the view.
    The main reason to have this util function is to facilitate mocking in unit tests for this view.
    """
    search_engine = SearchEngine(settings.SOLR_URL)
    results = search_engine.search(q)
    paginator = search_engine.return_paginator(results, settings.SOUNDS_PER_PAGE)
    page = paginator.page(current_page)
    return results.non_grouped_number_of_matches, results.facets, paginator, page, results.docs


def add_sounds_to_search_engine(sounds):
    search_engine = SearchEngine(settings.SOLR_URL)
    documents = [convert_to_search_engine_document(s) for s in sounds]
    console_logger.info("Adding %d sounds to solr index" % len(documents))
    search_logger.info("Adding %d sounds to solr index" % len(documents))
    search_engine.add_to_index(documents)


def add_all_sounds_to_search_engine(sound_queryset, slice_size=1000, mark_index_clean=False, delete_if_existing=False):
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
                delete_sounds_from_search_engine(sound_ids=sound_ids)
            add_sounds_to_search_engine(sounds_qs)

            if mark_index_clean:
                console_logger.info("Marking sounds as clean.")
                sounds.models.Sound.objects.filter(pk__in=sound_ids).update(is_index_dirty=False)
            num_correctly_indexed_sounds += len(sound_ids)
        except SearchEngineException as e:
            console_logger.error("failed to add sound batch to solr index, reason: %s", str(e))
            raise

    return num_correctly_indexed_sounds


def get_all_sound_ids_from_search_engine(limit=False):
    search_logger.info("getting all sound ids from solr.")
    if not limit:
        limit = 99999999999999
    search_engine = SearchEngine(settings.SOLR_URL)
    solr_ids = []
    solr_count = None
    PAGE_SIZE = 2000
    current_page = 1
    while (len(solr_ids) < solr_count or solr_count is None) and len(solr_ids) < limit:
        response = search_engine.search(search_prepare_query(
                '', '', search_prepare_sort('created asc', SEARCH_SORT_OPTIONS_WEB), current_page, PAGE_SIZE,
                include_facets=False))
        solr_ids += [element['id'] for element in response.docs]
        solr_count = response.num_found
        current_page += 1
    return sorted(solr_ids)


def check_if_sound_exists_in_search_egnine(sound):
    search_engine = SearchEngine(settings.SOLR_URL)
    response = search_engine.search(search_prepare_query(
            '', 'id:%i' % sound.id, search_prepare_sort('created asc', SEARCH_SORT_OPTIONS_WEB), 1, 1))
    return response.num_found > 0


def get_random_sound_from_search_engine():
    """ Get a random sound from solr.
    This is used for random sound browsing. We filter explicit sounds,
    but otherwise don't have any other restrictions on sound attributes
    """
    search_engine = SearchEngine(settings.SOLR_URL)
    query = QueryManager()
    rand_key = random.randint(1, 10000000)
    sort = ['random_%d asc' % rand_key]
    filter_query = 'is_explicit:0'
    query.set_query("*:*")
    query.set_query_options(start=0, rows=1, field_list=["*"], filter_query=filter_query, sort=sort)
    try:
        response = search_engine.search(query)
        docs = response.docs
        if docs:
            return docs[0]
    except (SearchEngineException, socket.error):
        pass
    return {}


def delete_sound_from_search_engine(sound_id):
    search_logger.info("deleting sound with id %d" % sound_id)
    try:
        SearchEngine(settings.SOLR_URL).remove_from_index(sound_id)
    except (SearchEngineException, socket.error) as e:
        search_logger.error('could not delete sound with id %s (%s).' % (sound_id, e))


def delete_sounds_from_search_engine(sound_ids):
    solr_max_boolean_clause = 1000  # This number is specified in solrconfig.xml
    for count, i in enumerate(range(0, len(sound_ids), solr_max_boolean_clause)):
        range_ids = sound_ids[i:i+solr_max_boolean_clause]
        try:
            search_logger.info(
                "deleting %i sounds from search engine [%i of %i, %i sounds]" %
                (len(sound_ids),
                 count + 1,
                 int(math.ceil(float(len(sound_ids)) / solr_max_boolean_clause)),
                 len(range_ids)))
            SearchEngine(settings.SOLR_URL).remove_documents_by_ids(range_ids)
            
        except (SearchEngineException, socket.error) as e:
            search_logger.error('could not delete solr sounds chunk %i of %i' %
                                (count + 1, int(math.ceil(float(len(sound_ids)) / solr_max_boolean_clause))))
