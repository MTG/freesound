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

from utils.search import SearchEngineException, get_search_engine, SearchResultsPaginator
import utils.search


search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def parse_weights_parameter(weights_param):
    """param weights can be used to specify custom field weights with this format 
    w=field_name1:integer_weight1,field_name2:integrer_weight2, eg: w=name:4,tags:1
    ideally, field names should any of those specified in settings.SEARCH_SOUNDS_FIELD_*
    so the search engine can implement ways to translate the "web names" to "search engine"
    names if needed.
    NOTE: this function is only used in the API
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


def add_sounds_to_search_engine(sound_objects, fields_to_include=[], update=False):
    """Add the Sounds from the queryset to the search engine

    Args:
        sound_objects (list[sounds.models.Sound]): list (or queryset) of Sound objects to index
        fields_to_include (list[str]): use this list to indicate the specific field names of the sounds 
            that need to be included in the documents that will be indexed. If no fields are specified 
            (fields_to_update=[]), then all available fields will be included.
        update (bool): if True, the sounds' data will be updated in the index, otherwise it will be 
            replaced by the new generated documents. This is specially useful in combination with
            fields_to_include so that different fields of the indexed can be updated separately. 

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
        get_search_engine().add_sounds_to_index(sound_objects, fields_to_include=fields_to_include, update=update)
        return num_sounds
    except SearchEngineException as e:
        console_logger.info(f"Failed to add sounds to search engine index: {str(e)}")
        search_logger.info(f"Failed to add sounds to search engine index: {str(e)}")
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
        console_logger.info(f"Could not delete sounds: {str(e)}")
        search_logger.info(f"Could not delete sounds: {str(e)}")


def delete_all_sounds_from_search_engine():
    """Delete all sounds from the search engine """
    console_logger.info("Deleting ALL sounds from search engine")
    search_logger.info("Deleting ALL sounds from search engine")
    try:
        get_search_engine().remove_all_sounds()
    except SearchEngineException as e:
        console_logger.info(f"Could not delete sounds: {str(e)}")
        search_logger.info(f"Could not delete sounds: {str(e)}")


def get_all_sound_ids_from_search_engine(page_size=2000):
    """Retrieves the list of all sound IDs currently indexed in the search engine

    Args:
        page_size: number of sound IDs to retrieve per search engine query

    Returns:
        list[int]: list of sound IDs indexed in the search engine
    """
    console_logger.info("Getting all sound ids from search engine")
    search_engine = get_search_engine()
    try:
        return search_engine.get_all_sound_ids_from_index()
    except SearchEngineException as e:
        search_logger.info(f"Could not retrieve all sound IDs from search engine: {str(e)}")


def get_random_sound_id_from_search_engine():
    # This helper function is used to facilitate unit testing and handle exception
    try:
        search_logger.info("Making random sound query")
        return get_search_engine().get_random_sound_id()
    except SearchEngineException as e:
        search_logger.info(f"Could not retrieve a random sound ID from search engine: {str(e)}")
    return 0

def get_sound_similarity_from_search_engine_query(query_params, analyzer_name=settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER, current_page=None, num_sounds=None):
    '''Gets the similarity vectors for the first "num_results" sounds for the given query.

    Args:
        query_params (dict): query parameters dictionary with parameters following the specification of search_sounds
            function from utils.search.SearchEngine.
        analyzer_name (str): name of the similarity analyzer from which to get the vector
        current_page (int): page number of the results to retrieve similarity vectors for. If None, the current page
            from query_params will be used.
        num_sounds (int): number of sounds to retrieve similarity vectors for. If None, the number of sounds
            in the query_params will be used.
    
    Returns:
        dict: dictionary with sound IDs as keys and similarity vectors as values
    '''

    # Update query params to get similarity vectors of the first 
    config_options = settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS[analyzer_name]
    vector_field_name = utils.search.backends.solr555pysolr.SOLR_VECTOR_FIELDS_DIMENSIONS_MAP.get(config_options['vector_size'])
    query_params.update({
        'facets': None,
        'current_page': current_page if current_page is not None else query_params['current_page'],
        'num_sounds': num_sounds if num_sounds is not None else query_params['num_sounds'],
        'field_list': ['id', 'score', 'similarity_vectors', 'sim_vector100', f'[child childFilter="content_type:v AND analyzer:{analyzer_name}" limit=1]']
    })
    results, _ = perform_search_engine_query(query_params)

    # Collect sound IDs and similarity vectors from query results
    similarity_vectors_map = {}
    for d in results.docs:
        if 'group_docs' in d:
            d0 = d['group_docs'][0]
        else:
            d0 = d
        if len(d0.get("similarity_vectors", [])) > 0:
            similarity_vectors_map[d0['id']] = d0["similarity_vectors"][0][vector_field_name]
    
    return similarity_vectors_map

def get_sound_ids_from_search_engine_query(query_params, current_page=None, num_sounds=None):
    """Performs Solr query and returns results as a list of sound ids.

    Args:
        query_params (dict): contains the query parameters to replicate the user query.
        current_page (int): page number of the results to retrieve IDs for. If None, the current page
            from query_params will be used.
        num_sounds (int): number of sounds to retrieve IDs for. If None, the number of sounds
            in the query_params will be used.
    
    Returns
        List[int]: list containing the ids of the retrieved sounds (for the current_page or num_sounds).
    """
    # We set include_facets to False in order to reduce the amount of data that search engine will return.
    query_params.update({
        'facets': None,
        'current_page': current_page if current_page is not None else query_params['current_page'],
        'num_sounds': num_sounds if num_sounds is not None else query_params['num_sounds'],
    })
    results, _ = perform_search_engine_query(query_params)
    resultids = [d.get("id") for d in results.docs]
    return resultids


def allow_beta_search_features(request):
     if not request.user.is_authenticated:
        return False
     if request.user.has_perm('profile.can_beta_test'):
        return True
