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

from django.conf import settings
from django.db.models.query import RawQuerySet
from urllib.parse import quote_plus
from pyparsing import ParseException

from utils.search import SearchEngineException, get_search_engine, SearchResultsPaginator
from utils.search.lucene_parser import parse_query_filter_string

search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def should_use_compact_mode(request):
    use_compact_mode_enabled_in_form = request.GET.get('cm')
    if not request.user.is_authenticated:
        return use_compact_mode_enabled_in_form == '1'
    else:
        if use_compact_mode_enabled_in_form is None:
            # Use user default
            return request.user.profile.use_compact_mode
        elif use_compact_mode_enabled_in_form == '1':
            # Use compact mode, but update user preferences if these differ from form value
            if use_compact_mode_enabled_in_form and not request.user.profile.use_compact_mode:
                request.user.profile.use_compact_mode = True
                request.user.profile.save()
            return True
        else:
            # Do not use compact mode, but update user preferences if these differ from form value
            if use_compact_mode_enabled_in_form and request.user.profile.use_compact_mode:
                request.user.profile.use_compact_mode = False
                request.user.profile.save()
            return False
        
def contains_active_advanced_search_filters(request, query_params, extra_vars):
    duration_filter_is_default = True
    if 'duration:' in query_params['query_filter']:
        if 'duration:[0 TO *]' not in query_params['query_filter']:
            duration_filter_is_default = False
    using_advanced_search_weights = request.GET.get("a_tag", False) \
        or request.GET.get("a_filename", False) \
        or request.GET.get("a_description", False) \
        or request.GET.get("a_packname", False) \
        or request.GET.get("a_soundid", False) \
        or request.GET.get("a_username", False)
    return using_advanced_search_weights \
        or extra_vars['fcw_license_filter'] \
        or 'is_geotagged:' in query_params['query_filter'] \
        or not duration_filter_is_default


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
    # If the query is through AJAX (for sources remix editing), do not collapse by pack
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

    # Set default values for field weights
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

    # if query param 'w' is present, override field weights
    weights_parameter = request.GET.get("w", "")
    custom_field_weights = parse_weights_parameter(weights_parameter)
    if custom_field_weights is not None:
        field_weights = custom_field_weights
   
    # parse query filter string and remove empty value fields
    parsing_error = False
    try:
        parsed_filters = parse_query_filter_string(filter_query)
    except ParseException:
        parsed_filters = []
        parsing_error = True

    # Process "free cultural works" filter stuff   
    fcw_license_filter = request.GET.get('fcw', False) == 'on'
    if fcw_license_filter:
        # If using fcw license filter, replace all other existing license filters for this one
        parsed_filters = [parsed_filter for parsed_filter in parsed_filters if parsed_filter[0] != 'license']
        parsed_filters.append(['license', ':', settings.FCW_FILTER_VALUE])
    else:
        # If not filtering by fcw, remove fcw filter if exists
        parsed_filters = [parsed_filter for parsed_filter in parsed_filters if parsed_filter[2] != settings.FCW_FILTER_VALUE]

    filter_query = ' '.join([''.join(filter_str) for filter_str in parsed_filters])

    filter_query_non_facets, has_facet_filter = remove_facet_filters(parsed_filters)

    query_params = {
        'textual_query': search_query,
        'query_filter': filter_query,
        'sort': sort,
        'current_page': current_page,
        'num_sounds': settings.SOUNDS_PER_PAGE if not should_use_compact_mode(request) else settings.SOUNDS_PER_PAGE_COMPACT_MODE,
        'query_fields': field_weights,
        'group_by_pack': group_by_pack,
        'only_sounds_with_pack': only_sounds_with_pack
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
        'parsing_error': parsing_error,
        'raw_weights_parameter': weights_parameter,
        'fcw_license_filter': fcw_license_filter
    }

    return query_params, advanced_search_params_dict, extra_vars


def parse_weights_parameter(weights_param):
    """param weights can be used to specify custom field weights with this format 
    w=field_name1:integer_weight1,field_name2:integrer_weight2, eg: w=name:4,tags:1
    ideally, field names should any of those specified in settings.SEARCH_SOUNDS_FIELD_*
    so the search engine can implement ways to translate the "web names" to "search engine"
    names if needed.
    """
    parsed_field_weights = {}
    if weights_param:
        for part in weights_param.split(','):
            if ':' in part:
                try:
                    field_name = part.split(':')[0]
                    weight = int(part.split(':')[1])
                    parsed_field_weights[field_name] = weight
                except Exception:
                    # If format is wrong, ignore parameter
                    pass
    if len(parsed_field_weights):
        return parsed_field_weights
    else:
        return None


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
            filter_value = filter_list_str[2]
            if filter_name != "duration" and filter_name != "is_geotagged" and filter_value != settings.FCW_FILTER_VALUE:
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
                        'remove_url': quote_plus(filter_query.replace(filter_str, '')),
                        'cluster_id': cluster_id,
                    }
                    filter_query_split.append(filter)

    # add cluster filter information
    if settings.ENABLE_SEARCH_RESULTS_CLUSTERING:
        if cluster_id and cluster_id.isdigit():
            filter_query_split.append({
                'name': "Cluster #" + cluster_id,
                'remove_url': quote_plus(filter_query),
                'cluster_id': '',
            })

    return filter_query_split


def remove_facet_filters(parsed_filters):
    """Process query filter string to keep only non facet filters

    Fact filters correspond to the filters that can be applied using one of the displayed facet in
    the search interface. This method is useful for being able to combine classic facet filters and clustering
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


def add_sounds_to_search_engine(sound_objects):
    """Add the Sounds from the queryset to the search engine

    Args:
        sound_objects (list[sounds.models.Sound]): list (or queryset) of Sound objects to index

    Returns:
        int: number of sounds added to the index
    """
    if isinstance(sound_objects, RawQuerySet):
        num_sounds = len(list(sound_objects))
    else:
        num_sounds = len(sound_objects)
    try:
        console_logger.info("Adding %d sounds to the search engine" % num_sounds)
        search_logger.info("Adding %d sounds to the search engine" % num_sounds)
        get_search_engine().add_sounds_to_index(sound_objects)
        return num_sounds
    except SearchEngineException as e:
        console_logger.error(f"Failed to add sounds to search engine index: {str(e)}")
        search_logger.error(f"Failed to add sounds to search engine index: {str(e)}")
        return 0


def delete_sounds_from_search_engine(sound_ids):
    """Delete sounds from the search engine

    Args:
        sound_ids (list[int]): IDs of the sounds to delete
    """
    console_logger.info(f"Deleting {len(sound_ids)} sounds from search engine")
    search_logger.info(f"Deleting {len(sound_ids)} sounds from search engine")
    try:
        get_search_engine().remove_sounds_from_index(sound_ids)
    except SearchEngineException as e:
        console_logger.error(f"Could not delete sounds: {str(e)}")
        search_logger.error(f"Could not delete sounds: {str(e)}")


def delete_all_sounds_from_search_engine():
    """Delete all sounds from the search engine """
    console_logger.info("Deleting ALL sounds from search engine")
    search_logger.info("Deleting ALL sounds from search engine")
    try:
        get_search_engine().remove_all_sounds()
    except SearchEngineException as e:
        console_logger.error(f"Could not delete sounds: {str(e)}")
        search_logger.error(f"Could not delete sounds: {str(e)}")


def get_all_sound_ids_from_search_engine(page_size=2000):
    """Retrieves the list of all sound IDs currently indexed in the search engine

    Args:
        page_size: number of sound IDs to retrieve per search engine query

    Returns:
        list[int]: list of sound IDs indexed in the search engine
    """
    console_logger.info("Getting all sound ids from search engine")
    search_engine = get_search_engine()
    solr_ids = []
    solr_count = None
    current_page = 1
    try:
        while solr_count is None or len(solr_ids) < solr_count:
            response = search_engine.search_sounds(query_filter="*:*",
                                                   sort=settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST,
                                                   offset=(current_page - 1) * page_size,
                                                   num_sounds=page_size)
            solr_ids += [element['id'] for element in response.docs]
            solr_count = response.num_found
            current_page += 1
    except SearchEngineException as e:
        search_logger.error(f"Could not retrieve all sound IDs from search engine: {str(e)}")
    return sorted(solr_ids)


def get_random_sound_id_from_search_engine():
    # This helper function is used to facilitate unit testing and handle exception
    try:
        search_logger.info("Making random sound query")
        return get_search_engine().get_random_sound_id()
    except SearchEngineException as e:
        search_logger.error(f"Could not retrieve a random sound ID from search engine: {str(e)}")
    return 0
