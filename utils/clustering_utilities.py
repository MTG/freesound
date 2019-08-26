import traceback, logging
from django.conf import settings
from django.core.cache import cache
from clustering.client import Clustering
from clustering.clustering_settings import CLUSTERING_CACHE_TIME
from utils.encryption import create_hash
from utils.search.search_general import search_prepare_query, perform_solr_query
import copy

logger = logging.getLogger('web')


def get_sound_ids_from_solr_query(query_params, num_sounds=1000):
    current_page = 1  # for what is this used for??
    query_params.update({'sounds_per_page': num_sounds})
    query = search_prepare_query(**query_params)
    non_grouped_number_of_results, facets, paginator, page, docs = perform_solr_query(query, current_page)
    resultids = [d.get("id") for d in docs]
    return resultids


def cluster_sound_results(query_params, features):
    query_params_formatted = copy.copy(query_params)
    query_params_formatted['filter_query'] = query_params_formatted['filter_query'].replace('\\"', '"')

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
    if len(cache_key) >= 250:
        returned_sounds = False
    else:
        result = cache.get(cache_key_hashed)
        if result:
            returned_sounds = result[0]
            graph = result[1]
        else:
            returned_sounds = False

    # if not in cache, query solr and perform clustering
    if not returned_sounds:
        sound_ids = get_sound_ids_from_solr_query(query_params_formatted)
        sound_ids_string = ','.join([str(sound_id) for sound_id in sound_ids])

        result = Clustering.cluster_points(
            query=cache_key,
            sound_ids=sound_ids_string,
            features=features
        )

        returned_sounds = result[0]
        graph = result[1]

        if len(returned_sounds) > 0 and len(cache_key) < 250:
            cache.set(cache_key_hashed, result, CLUSTERING_CACHE_TIME)

    try:
        num_clusters = len(returned_sounds) + 1
    except ValueError:
        num_clusters = 0

    return returned_sounds, num_clusters, graph


def hash_cache_key(key):
    return create_hash(key, add_secret=False, limit=32)
