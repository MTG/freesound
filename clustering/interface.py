import copy
import traceback, logging
from django.conf import settings
from django.core.cache import cache
from utils.encryption import create_hash
from utils.search.search_general import search_prepare_query, perform_solr_query, \
    search_prepare_parameters

from tasks import cluster_sound_results_celery
from clustering_settings import clustering_settings as clust_settings

CLUSTERING_CACHE_TIME = clust_settings.get('CLUSTERING_CACHE_TIME')

logger = logging.getLogger('clustering')


def get_sound_ids_from_solr_query(query_params, num_sounds=1000):
    current_page = 1  # for what is this used for??
    query_params.update({'sounds_per_page': num_sounds})
    query = search_prepare_query(**query_params)
    non_grouped_number_of_results, facets, paginator, page, docs = perform_solr_query(query, current_page)
    resultids = [d.get("id") for d in docs]
    return resultids


def cluster_sound_results(request, features):
    query_params, _ = search_prepare_parameters(request)
    # query_params_formatted = copy.copy(query_params)
    # query_params_formatted['filter_query'] = query_params_formatted['filter_query'].replace('\\"', '"')

    cache_key = 'cluster-search-results-q-{}-f-{}-s-{}-tw-{}-uw-{}-idw-{}-dw-{}-pw-{}-fw-{}-g-{}-feat-{}'.format(
        query_params['search_query'],
        query_params['filter_query'],
        str(query_params['sort'][0]),  # str cast to avoid having sometimes unicode != string
        query_params['tag_weight'],
        query_params['username_weight'],
        query_params['id_weight'],
        query_params['description_weight'],
        query_params['pack_tokenized_weight'],
        query_params['original_filename_weight'],
        query_params['grouping'],
        features,
    ).replace(' ', '')

    cache_key_hashed = hash_cache_key(cache_key)

    # check if result is in cache
    result = cache.get(cache_key_hashed)

    if result and result not in ('pending', 'failed'):
        # reset the value in cache so that it presist
        cache.set(cache_key_hashed, result, CLUSTERING_CACHE_TIME)

        result.update({'finished': True, 'error': False})
        
        return result

    elif result == 'pending':
        return {'finished': False, 'error': False}

    elif result == 'failed':
        return {'finished': False, 'error': True}

    else:
        # if not in cache, query solr and perform clustering
        sound_ids = get_sound_ids_from_solr_query(query_params)
        sound_ids_string = ','.join([str(sound_id) for sound_id in sound_ids])

        # launch celery async task
        cluster_sound_results_celery.delay(cache_key_hashed, sound_ids_string, features)

        return {'finished': False, 'error': False}


def hash_cache_key(key):
    return create_hash(key, add_secret=False, limit=32)
