from django.core.cache import cache
from celery.decorators import task

from clustering_settings import CLUSTERING_CACHE_TIME, CLUSTERING_PENDING_CACHE_TIME
from . import CLUSTERING_RESULT_STATUS_PENDING, CLUSTERING_RESULT_STATUS_FAILED


@task(name="cluster_sounds")
def cluster_sounds(cache_key_hashed, sound_ids, features):
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
