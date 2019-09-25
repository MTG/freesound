from django.core.cache import cache
from celery.decorators import task

from clustering_settings import CLUSTERING_CACHE_TIME, CLUSTERING_PENDING_CACHE_TIME
from . import CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED


@task(name="cluster_sounds")
def cluster_sounds(cache_key_hashed, sound_ids, features):
    # this import would be better outside the function, but did not work
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
