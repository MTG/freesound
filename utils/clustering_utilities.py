import traceback, logging
from django.conf import settings
from django.core.cache import cache
from clustering.client import Clustering
from clustering.clustering_settings import CLUSTERING_CACHE_TIME
from utils.encryption import create_hash
from utils.search.search_general import search_prepare_query, perform_solr_query

logger = logging.getLogger('web')


def get_sound_ids_from_solr_query(query_params):
    current_page = 1  # for what is this used for??
    # with more sounds solr says 'URI is too large >8192'
    query_params.update({'sounds_per_page': 800})
    query_params['filter_query'] = query_params['filter_query'].replace('\\\"', '"')
    query = search_prepare_query(**query_params)
    non_grouped_number_of_results, facets, paginator, page, docs = perform_solr_query(query, current_page)
    resultids = [d.get("id") for d in docs]
    return resultids


def cluster_sound_results(query_params):
    # fake sound ids to request clustering
    # fake_sound_ids = '262436,213079,325667'

    cache_key = 'cluster-search-results-q-{}-f-{}-s-{}-tw-{}-uw-{}-idw-{}-dw-{}-pw-{}-fw-{}'.format(
        query_params['search_query'],
        query_params['filter_query'],
        str(query_params['sort'][0]),  # str cast to avoid having sometimes unicode != string
        query_params['tag_weight'],
        query_params['username_weight'],
        query_params['id_weight'],
        query_params['description_weight'],
        query_params['pack_tokenized_weight'],
        query_params['original_filename_weight'],
    )    

    cache_key_hashed = hash_cache_key(cache_key)

    # check if result is in cache
    if len(cache_key) >= 250:
        returned_sounds = False
    else:
        result = cache.get(cache_key_hashed)
        if result:
            returned_sounds = result
        else:
            returned_sounds = False

    # if not in cache, query solr and perform clustering
    if not returned_sounds:
        sound_ids = get_sound_ids_from_solr_query(query_params)
        sound_ids_string = ','.join([str(sound_id) for sound_id in sound_ids])

        result = Clustering.cluster_points(
            query=cache_key,
            sound_ids=sound_ids_string,
        )

        # fake results for now
        # result = {
        #     sound_id: idx%2 for idx, sound_id in enumerate(sound_ids)
        # }

        returned_sounds = result

        if len(returned_sounds) > 0 and len(cache_key) < 250:
            cache.set(cache_key_hashed, result, CLUSTERING_CACHE_TIME)

    num_clusters = max(returned_sounds.values()) + 1

    return returned_sounds, num_clusters


def hash_cache_key(key):
    return create_hash(key, add_secret=False, limit=32)
