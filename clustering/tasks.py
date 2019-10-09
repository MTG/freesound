from django.core.cache import cache
from celery.decorators import task
import logging

from clustering_settings import CLUSTERING_CACHE_TIME, CLUSTERING_PENDING_CACHE_TIME
from . import CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED

logger = logging.getLogger('clustering')


@task(name="cluster_sounds")
def cluster_sounds(cache_key_hashed, sound_ids, features):
    """ Triggers the clustering of the sounds given as argument with the specified features.

    This is the task that is used for clustering the sounds of a search result asynchronously with Celery.
    The clustering result is stored in cache using the hashed cache key built with the query parameters.

    Args:
        cache_key_hashed (str): hashed key for storing/retrieving the results in cache.
        sound_ids (str): string containing comma-separated sound ids.
        features (str): name of the features used for clustering the sounds (defined in the clustering settings file).
    """
    # This ensures that the engine is imported after it is re-assigned in __init__.py
    # There should be a better way to do it to avoid multiple imports that can decrease performance
    from . import engine

    # store pending state in cache
    cache.set(cache_key_hashed, CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_PENDING_CACHE_TIME)

    try:
        # perform clustering
        result = engine.cluster_points(cache_key_hashed, features, sound_ids)

        # store result in cache
        cache.set(cache_key_hashed, result, CLUSTERING_CACHE_TIME)

    except Exception as e:  
        # delete pending state if exception raised during clustering
        cache.set(cache_key_hashed, CLUSTERING_RESULT_STATUS_FAILED, CLUSTERING_PENDING_CACHE_TIME)
        logger.error("Exception raised while clustering sounds", exc_info=True)
