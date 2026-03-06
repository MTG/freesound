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

import sounds.models
import utils.search
from utils.search import SearchEngineException, SearchResultsPaginator, get_search_engine

search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def parse_weights_parameter(weights_param):
    """param weights can be used to specify custom field weights with this format
    w=field_name1:integer_weight1,field_name2:integer_weight2, eg: w=name:4,tags:1
    ideally, field names should any of those specified in settings.SEARCH_SOUNDS_FIELD_*
    so the search engine can implement ways to translate the "web names" to "search engine"
    names if needed.
    NOTE: this function is only used in the API
    """
    parsed_field_weights = {}
    if weights_param:
        for part in weights_param.split(","):
            if ":" in part:
                try:
                    field_name = part.split(":")[0]
                    weight = int(part.split(":")[1])
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
    paginator = SearchResultsPaginator(results, query_params["num_sounds"])

    return results, paginator


def add_sounds_to_search_engine(
    sound_objects: list["sounds.models.Sound"], update=False, include_similarity_vectors=False, solr_collection_url=None
):
    """Add the Sounds from the queryset to the search engine

    Args:
        sound_objects: list (or queryset) of Sound objects to index
    Returns:
        int: number of sounds added to the index
    """
    if isinstance(sound_objects, RawQuerySet):
        num_sounds = len(list(sound_objects))
    else:
        num_sounds = len(sound_objects)
    try:
        console_logger.debug(f"Adding {num_sounds} sounds to the search engine")
        search_logger.debug(f"Adding {num_sounds} sounds to the search engine")
        get_search_engine(sounds_index_url=solr_collection_url).add_sounds_to_index(
            sound_objects, update=update, include_similarity_vectors=include_similarity_vectors
        )
        return num_sounds
    except SearchEngineException as e:
        console_logger.error(f"Failed to add sounds to search engine index: {str(e)}")
        search_logger.error(f"Failed to add sounds to search engine index: {str(e)}")
        return 0


def send_update_similarity_vectors_in_search_engine(
    sound_objects: list["sounds.models.Sound"], solr_collection_url=None
):
    """Update the similarity vectors for the Sounds from the queryset in the search engine

    Args:
        sound_objects: list (or queryset) of Sound objects to index
    Returns:
        int: number of sounds added to the index
    """
    if isinstance(sound_objects, RawQuerySet):
        num_sounds = len(list(sound_objects))
    else:
        num_sounds = len(sound_objects)
    try:
        console_logger.debug(f"Adding similarity vectors for {num_sounds} sounds to the search engine")
        search_logger.debug(f"Adding similarity vectors for {num_sounds} sounds to the search engine")
        get_search_engine(sounds_index_url=solr_collection_url).update_similarity_vectors_in_index(sound_objects)
        return num_sounds
    except SearchEngineException as e:
        console_logger.error(f"Failed to add sounds to search engine index: {str(e)}")
        search_logger.error(f"Failed to add sounds to search engine index: {str(e)}")
        return 0


def delete_sounds_from_search_engine(sound_ids, solr_collection_url=None):
    """Delete sounds from the search engine

    Args:
        sound_ids (list[int]): IDs of the sounds to delete
    """
    console_logger.info(f"Deleting {len(sound_ids)} sounds from search engine")
    search_logger.info(f"Deleting {len(sound_ids)} sounds from search engine")
    try:
        get_search_engine(sounds_index_url=solr_collection_url).remove_sounds_from_index(sound_ids)
    except SearchEngineException as e:
        console_logger.info(f"Could not delete sounds: {str(e)}")
        search_logger.info(f"Could not delete sounds: {str(e)}")


def delete_all_sounds_from_search_engine(solr_collection_url=None):
    """Delete all sounds from the search engine"""
    console_logger.info("Deleting ALL sounds from search engine")
    search_logger.info("Deleting ALL sounds from search engine")
    try:
        get_search_engine(sounds_index_url=solr_collection_url).remove_all_sounds()
    except SearchEngineException as e:
        console_logger.info(f"Could not delete sounds: {str(e)}")
        search_logger.info(f"Could not delete sounds: {str(e)}")


def get_all_sound_ids_from_search_engine(solr_collection_url=None):
    """Retrieves the list of all sound IDs currently indexed in the search engine

    Args:
        page_size: number of sound IDs to retrieve per search engine query

    Returns:
        list[int]: list of sound IDs indexed in the search engine
    """
    console_logger.info("Getting all sound ids from search engine")
    search_engine = get_search_engine(sounds_index_url=solr_collection_url)
    try:
        return search_engine.get_all_sound_ids_from_index()
    except SearchEngineException as e:
        search_logger.info(f"Could not retrieve all sound IDs from search engine: {str(e)}")
    return []


def get_all_sim_vector_sound_ids_from_search_engine(solr_collection_url=None):
    """Retrieves the list of all sound IDs with similarity vectors for all similarity spaces currently
    indexed in the search engine

    Args:
        page_size: number of sound IDs to retrieve per search engine query

    Returns:
        dict[list]: list of sound IDs with per similarity space indexed in the search engine
    """
    console_logger.info("Getting all sound ids with similarity vectors from search engine")
    search_engine = get_search_engine(sounds_index_url=solr_collection_url)
    sim_vector_sound_ids = {}
    try:
        sim_vector_document_ids = search_engine.get_all_sim_vector_document_ids_per_similarity_space()
        for key, document_ids in sim_vector_document_ids.items():
            sim_vector_sound_ids[key] = list(set([int(doc_id.split("/")[0]) for doc_id in document_ids]))
    except SearchEngineException as e:
        search_logger.info(
            f"Could not retrieve all sound IDs with similarity vectors for similarity space from search engine: {str(e)}"
        )
    return sim_vector_sound_ids


def get_random_sound_id_from_search_engine(solr_collection_url=None):
    # This helper function is used to facilitate unit testing and handle exception
    try:
        search_logger.info("Making random sound query")
        return get_search_engine(sounds_index_url=solr_collection_url).get_random_sound_id()
    except SearchEngineException as e:
        search_logger.info(f"Could not retrieve a random sound ID from search engine: {str(e)}")
    return 0


def get_sound_similarity_vectors_from_search_engine_query(
    query_params, similarity_space=settings.SIMILARITY_SPACE_DEFAULT, current_page=None, num_sounds=None
):
    """Gets the similarity vectors for the first "num_results" sounds for the given query.

    Args:
        query_params (dict): query parameters dictionary with parameters following the specification of search_sounds
            function from utils.search.SearchEngine.
        similarity_space (str): name of the similarity space from which to get the vector
        current_page (int): page number of the results to retrieve similarity vectors for. If None, the current page
            from query_params will be used.
        num_sounds (int): number of sounds to retrieve similarity vectors for. If None, the number of sounds
            in the query_params will be used.

    Returns:
        dict: dictionary with sound IDs as keys and similarity vectors as values
    """
    # Update query params to get similarity vectors of the first
    config_options = settings.SIMILARITY_SPACES[similarity_space]
    vector_field_name = utils.search.backends.solr555pysolr.get_solr_dense_vector_search_field_name(
        config_options["vector_size"], config_options.get("l2_norm", False)
    )
    query_params.update(
        {
            "facets": None,
            "current_page": current_page if current_page is not None else query_params["current_page"],
            "num_sounds": num_sounds if num_sounds is not None else query_params["num_sounds"],
            "field_list": [
                "id",
                "score",
                "similarity_vectors",
                vector_field_name,
                f'[child childFilter="content_type:v AND similarity_space:{similarity_space}" limit=1]',
            ],
        }
    )
    results, _ = perform_search_engine_query(query_params)

    # Collect sound IDs and similarity vectors from query results
    similarity_vectors_map = {}
    for d in results.docs:
        if "group_docs" in d:
            d0 = d["group_docs"][0]
        else:
            d0 = d
        d0_sim_vectors = d0.get("similarity_vectors", [])
        if len(d0_sim_vectors) > 0:
            if type(d0_sim_vectors) == dict:
                d0_sim_vectors = [d0_sim_vectors]
            similarity_vectors_map[d0["id"]] = d0_sim_vectors[0][vector_field_name]

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
    query_params.update(
        {
            "facets": None,
            "current_page": current_page if current_page is not None else query_params["current_page"],
            "num_sounds": num_sounds if num_sounds is not None else query_params["num_sounds"],
        }
    )
    results, _ = perform_search_engine_query(query_params)
    resultids = [d.get("id") for d in results.docs]
    return resultids


def allow_beta_search_features(request):
    if not request.user.is_authenticated:
        return False
    if request.user.has_perm("accounts.can_beta_test"):
        return True


def get_empty_query_cache_key(request, use_beta_features=None):
    if not settings.SEARCH_EMPTY_QUERY_CACHE_KEY:
        return False
    if use_beta_features is None:
        # If not specified, we check if the user has beta features enabled
        use_beta_features = allow_beta_search_features(request)
    return (
        settings.SEARCH_EMPTY_QUERY_CACHE_KEY
        if not use_beta_features
        else settings.SEARCH_EMPTY_QUERY_CACHE_KEY + "_beta"
    )
