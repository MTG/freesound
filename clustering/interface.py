import copy
import traceback, logging
from django.conf import settings
from django.core.cache import cache
from utils.encryption import create_hash
from utils.search.search_general import search_prepare_query, perform_solr_query, \
    search_prepare_parameters

from tasks import cluster_sounds
from clustering_settings import MAX_RESULTS_FOR_CLUSTERING, CLUSTERING_CACHE_TIME, DEFAULT_FEATURES
from . import CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED


def get_sound_ids_from_solr_query(query_params):
    """Performs Solr query on the Freesound audio collection.

    Args:
        query_params (dict): contains the query parameters to replicate the user query.
    
    Returns
        List[int]: list containing the ids of the retrieved sounds.
    """
    current_page = 1
    query_params.update({'sounds_per_page': MAX_RESULTS_FOR_CLUSTERING})
    query = search_prepare_query(**query_params)
    non_grouped_number_of_results, facets, paginator, page, docs = perform_solr_query(query, current_page)
    resultids = [d.get("id") for d in docs]
    return resultids


def cluster_sound_results(request, features=DEFAULT_FEATURES):
    """Performs clustering on the search results of the fiven request with the requested features.

    This is the main entry to the clustering method. It will either get the clustering results from cache, 
    or compute it (and store it in cache). When needed, the clustering will be performed async by a celery 
    worker. 

    Args:
        request (HttpRequest): request associated with the search query submited by the user.
        features (str): name of the features to be used for clustering. The available features are defined in the 
        clustering settings file.

    Returns:
        Dict: contains either the state of the clustering ('pending' or 'failed') or the resulting clustering classes 
            and the graph in node-link format suitable for JSON serialization.
    """
    query_params, _, _ = search_prepare_parameters(request)

    cache_key = 'cluster-results-{search_query}-{filter_query}-{sort}-{tag_weight}-{username_weight}-{id_weight}-' \
                '{description_weight}-{pack_tokenized_weight}-{original_filename_weight}-{grouping}'.format(**query_params)

    cache_key += '-{}'.format(features)
    cache_key = cache_key.replace(' ', '')

    cache_key_hashed = hash_cache_key(cache_key)

    # check if result is in cache
    result = cache.get(cache_key_hashed)

    if result and result not in (CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED):
        # reset the value in cache so that it presists
        cache.set(cache_key_hashed, result, CLUSTERING_CACHE_TIME)
        result.update({'finished': True, 'error': False})

        return result

    elif result == CLUSTERING_RESULT_STATUS_PENDING:
        return {'finished': False, 'error': False}

    elif result == CLUSTERING_RESULT_STATUS_FAILED:
        return {'finished': False, 'error': True}

    else:
        # if not in cache, query solr and perform clustering
        sound_ids = get_sound_ids_from_solr_query(query_params)
        sound_ids_string = ','.join([str(sound_id) for sound_id in sound_ids])

        # launch clustering with celery async task
        cluster_sounds.delay(cache_key_hashed, sound_ids_string, features)

        return {'finished': False, 'error': False}


def hash_cache_key(key):
    return create_hash(key, add_secret=False, limit=32)
