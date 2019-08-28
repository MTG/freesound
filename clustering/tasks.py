from django.core.cache import cache
from celery.decorators import task
from clustering_settings import CLUSTERING_CACHE_TIME, CLUSTERING_PENDING_CACHE_TIME


@task(name="cluster_points")
def cluster_sound_results_celery(cache_key_hashed, sound_ids, features):
    from . import engine

    # store pending state in cache
    cache.set(cache_key_hashed, 'pending', CLUSTERING_PENDING_CACHE_TIME)

    try:
        # perform clustering
        result = engine.cluster_points(cache_key_hashed, features, sound_ids)

        # store result in cache
        cache.set(cache_key_hashed, result, CLUSTERING_CACHE_TIME)
        print(cache_key_hashed)

    except:  # delete pending state if exception raised during clustering
        cache.delete(cache_key_hashed)
