import traceback, logging
from django.conf import settings
from django.core.cache import cache
from clustering.client import Clustering
from clustering.clustering_settings import CLUSTERING_CACHE_TIME
from utils.encryption import create_hash


logger = logging.getLogger('web')


def get_clusters(sound_ids, query=None, filter=None):

    cache_key = 'cluster-sounds-q-%s-f-%s' % (str(query).replace(" ", ""), str(filter).replace(" ", ""))
    cache_key = hash_cache_key(cache_key)

    # Don't use the cache when we're debugging
    if settings.DEBUG or len(cache_key) >= 250:
        returned_sounds = False
    else:
        result = cache.get(cache_key)
        if result:
            returned_sounds = result
        else:
            returned_sounds = False

    if not returned_sounds:
        result = Clustering.cluster_points(
            query=query,
            sound_ids=sound_ids,
        )

        returned_sounds = result

        if len(returned_sounds) > 0 and len(cache_key) < 250 and not settings.DEBUG:
            cache.set(cache_key, result, CLUSTERING_CACHE_TIME)
    
    num_clusters = max(result.values()) + 1

    return returned_sounds, num_clusters


def hash_cache_key(key):
    return create_hash(key, add_secret=False, limit=32)
