import settings, traceback, logging
from sounds.models import Sound
from django.core.cache import cache
from similarity.client.similarity_client import Similarity
from similarity.similarity_settings import PRESETS, DEFAULT_PRESET, SIMILAR_SOUNDS_TO_CACHE, SIMILARITY_CACHE_TIME

logger = logging.getLogger('web')

def get_similar_sounds(sound, preset = DEFAULT_PRESET, num_results = settings.SOUNDS_PER_PAGE ):

    if preset not in PRESETS:
        preset = DEFAULT_PRESET

    cache_key = "similar-for-sound-%s-%s" % (sound.id, preset)

    # Don't use the cache when we're debugging
    if settings.DEBUG:
        similar_sounds = False
    else:
        similar_sounds = cache.get(cache_key)

    if not similar_sounds:
        try:
            similar_sounds = [ [int(x[0]),float(x[1])] for x in Similarity.search(sound.id, preset = preset, num_results = SIMILAR_SOUNDS_TO_CACHE)]
        except Exception, e:
            logger.debug('Could not get a response from the similarity service (%s)\n\t%s' % \
                         (e, traceback.format_exc()))
            similar_sounds = []

        if len(similar_sounds) > 0:
            cache.set(cache_key, similar_sounds, SIMILARITY_CACHE_TIME)

    return similar_sounds[0:num_results]


def query_for_descriptors(target, filter, num_results = settings.SOUNDS_PER_PAGE):
    target = target.replace(" ","")
    filter = filter.replace(" ","")
    cache_key = "content-based-search-t-%s-f-%s-nr-%s" % (target,filter,num_results)

    # Don't use the cache when we're debugging
    if settings.DEBUG:
        returned_sounds = False
    else:
        returned_sounds = cache.get(cache_key)

    if not returned_sounds:
        try:
            returned_sounds = [ [int(x[0]),float(x[1])] for x in Similarity.query(target, filter, num_results)]
        except Exception, e:
            logger.info('Could not get a response from the similarity service (query for descriptors) (%s)\n\t%s' %\
                         (e, traceback.format_exc()))
            returned_sounds = []#[-999]

        if len(returned_sounds) > 0:# and returned_sounds[0] != -999:
            cache.set(cache_key, returned_sounds, SIMILARITY_CACHE_TIME)

    return returned_sounds[0:num_results]