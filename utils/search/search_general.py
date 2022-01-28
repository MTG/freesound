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

from django.conf import settings
from django.utils.http import urlquote_plus
from pyparsing import ParseException

import sounds
from utils.search import SearchEngineException, get_search_engine, SearchResultsPaginator
from utils.search.lucene_parser import parse_query_filter_string

search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def search_prepare_parameters(request):
    """Parses and pre-process search input parameters from the search view request object and returns them as a dict.

    From the request object, it constructs a dict with query parameters which will be compatible with
    utils.search.SearchEngine.search_sounds(...) parameters. Additionally, other variables are returned which
    are used for logging purpose and for building the search view context variables.

    Args:
        request (HttpRequest): request associated with the search query submitted by the user.

    Returns:
        Tuple(dict, dict, dict): 3-element tuple containing the query parameters compatible with the search_sounds,
            method from SearchEngine, the search params used for logging, and some extra parameters needed in
            the search view.
    """
    search_query = request.GET.get("q", "")
    filter_query = request.GET.get("f", "").strip().lstrip()
    cluster_id = request.GET.get('cluster_id', "")

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1
    sort = request.GET.get("s", None)

    if search_query == "" and sort is None:
        # When making empty queries and no sorting is specified, automatically set sort to "created desc" as
        # relevance score based sorting makes no sense
        sort = settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST

    # If the query is filtered by pack, do not collapse sounds of the same pack (makes no sense)
    # If the query is through AJAX (for sources remix editing), do not collapse
    group_by_pack = request.GET.get("g", "1") == "1"  # Group by default

    if "pack" in filter_query or request.GET.get("ajax", "") == "1":
        group_by_pack = False

    # If the query is filtered by pack, do not add the "only sounds with pack" filter (makes no sense)
    only_sounds_with_pack = request.GET.get("only_p", "0") == "1"  # By default, do not limit to sounds with pack
    if "pack" in filter_query:
        only_sounds_with_pack = False

    # If the query is displaying only sounds with pack, also enable group by pack as this is needed to display
    # results as packs
    if only_sounds_with_pack:
        group_by_pack = True

    # Set default values
    id_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_ID]
    tag_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_TAGS]
    description_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_DESCRIPTION]
    username_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_USER_NAME]
    pack_tokenized_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_PACK_NAME]
    original_filename_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_NAME]

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

        # If none is selected use all (so other filter can be applied)
        if a_tag != "" or a_filename != "" or a_description != "" or a_packname != "" or a_soundid != "" \
                or a_username != "":

            # Initialize all weights to 0
            id_weight = 0
            tag_weight = 0
            description_weight = 0
            username_weight = 0
            pack_tokenized_weight = 0
            original_filename_weight = 0

            # Set the weights of selected checkboxes
            if a_soundid != "":
                id_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_ID]
            if a_tag != "":
                tag_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_TAGS]
            if a_description != "":
                description_weight = \
                    settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_DESCRIPTION]
            if a_username != "":
                username_weight = settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_USER_NAME]
            if a_packname != "":
                pack_tokenized_weight = \
                    settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_PACK_NAME]
            if a_filename != "":
                original_filename_weight = \
                    settings.SEARCH_SOUNDS_DEFAULT_FIELD_WEIGHTS[settings.SEARCH_SOUNDS_FIELD_NAME]

    field_weights = {
        settings.SEARCH_SOUNDS_FIELD_ID: id_weight,
        settings.SEARCH_SOUNDS_FIELD_TAGS: tag_weight,
        settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: description_weight,
        settings.SEARCH_SOUNDS_FIELD_USER_NAME: username_weight,
        settings.SEARCH_SOUNDS_FIELD_PACK_NAME: pack_tokenized_weight,
        settings.SEARCH_SOUNDS_FIELD_NAME: original_filename_weight
    }

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
        'textual_query': search_query,
        'query_filter': filter_query,
        'sort': sort,
        'current_page': current_page,
        'num_sounds': settings.SOUNDS_PER_PAGE,
        'query_fields': field_weights,
        'group_by_pack': group_by_pack,
        'only_sounds_with_pack': only_sounds_with_pack,
    }

    filter_query_link_more_when_grouping_packs = filter_query.replace(' ', '+')

    # These variables are not used for querying the sound collection
    # We keep them separated in order to facilitate the distinction between variables used for performing
    # the Solr query and these extra ones needed for rendering the search template page
    extra_vars = {
        'filter_query_link_more_when_grouping_packs': filter_query_link_more_when_grouping_packs,
        'advanced': advanced,
        'cluster_id': cluster_id,
        'filter_query_non_facets': filter_query_non_facets,
        'has_facet_filter': has_facet_filter,
        'parsed_filters': parsed_filters,
        'parsing_error': parsing_error
    }

    return query_params, advanced_search_params_dict, extra_vars


def split_filter_query(filter_query, parsed_filters, cluster_id):
    """Pre-process parsed search filter parameters and returns the filters' information.

    This function is used in the search template to display the filter and the link when removing them.
    The cluster ID is provided separated from the parsed filters in order to keep clustering explicitly
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


def remove_facet_filters(parsed_filters):
    """Process query filter string to keep only non facet filters

    Fact filters correspond to the filters that can be applied using one of the displayed facet in
    the search interface. It is useful for being able to combine classic facet filters and clustering
    because clustering has to be done on the results of a search without applying facet filters (we want
    to have the clustering facet behaving as a traditional facet, meaning that the clustering should not 
    be re-triggered when applying new facet filters on the results).
    Additionally, it returns a boolean that indicates if a facet filter was present in the query.

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


def perform_search_engine_query(query_params):
    """Perform a query in the search engine given some query parameters and get the paginated results

    This util function performs the query to the search engine and returns needed parameters to continue with the view.
    The main reason to have this util function is to facilitate mocking in unit tests for this view.

    Args:
        query_params (dict): query parameters dictionary with parameters following the specification of search_sounds
            function from utils.search.SearchEngine.

    Returns:
        utils.search.SearchResults: search results object with query results from the search engine
        utils.search.SearchResultsPaginator: paginator object for the selected page according to query_params
    """
    results = get_search_engine().search_sounds(**query_params)
    paginator = SearchResultsPaginator(results, query_params['num_sounds'])
    return results, paginator


def add_sounds_to_search_engine(sounds):
    search_engine = get_search_engine()
    documents = [search_engine.convert_sound_to_search_engine_document(s) for s in sounds]
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
            num_sounds = sounds_qs.count()
            if delete_if_existing:
                delete_sounds_from_search_engine(sound_ids=sound_ids)

            console_logger.info("Adding %d sounds to solr index" % num_sounds)
            search_logger.info("Adding %d sounds to solr index" % num_sounds)
            get_search_engine().add_sounds_to_index(sounds_qs)

            if mark_index_clean:
                console_logger.info("Marking sounds as clean.")
                sounds.models.Sound.objects.filter(pk__in=sound_ids).update(is_index_dirty=False)
            num_correctly_indexed_sounds += len(sound_ids)
        except SearchEngineException as e:
            console_logger.error("Failed to add sound batch to solr index, reason: %s", str(e))
            raise

    return num_correctly_indexed_sounds


def get_all_sound_ids_from_search_engine(limit=False):
    search_logger.info("getting all sound ids from search engine.")
    if not limit:
        limit = 99999999999999
    search_engine = get_search_engine()
    solr_ids = []
    solr_count = None
    PAGE_SIZE = 2000
    current_page = 1
    while (len(solr_ids) < solr_count or solr_count is None) and len(solr_ids) < limit:
        response = search_engine.search_sounds(sorting=settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,
                                               offset=(current_page - 1) * PAGE_SIZE,
                                               num_sounds=PAGE_SIZE)
        solr_ids += [element['id'] for element in response.docs]
        solr_count = response.num_found
        current_page += 1
    return sorted(solr_ids)


def get_random_sound_id_from_search_engine():
    # We use this helper function as it facilitates unit testing
    return get_search_engine().get_random_sound()


def delete_sound_from_search_engine(sound_id):
    search_logger.info("deleting sound with id %d" % sound_id)
    try:
        get_search_engine().remove_from_index(sound_id)
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
            get_search_engine().remove_from_index_by_ids(range_ids)
            
        except (SearchEngineException, socket.error) as e:
            search_logger.error('could not delete solr sounds chunk %i of %i' %
                                (count + 1, int(math.ceil(float(len(sound_ids)) / solr_max_boolean_clause))))
