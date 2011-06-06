from django.conf import settings
from sounds.models import Sound
from django.core.cache import cache
from similarity.client import Similarity

DEFAULT_SIMILARITY_PRESET = 'lowlevel'

def get_similar_sounds(sound, preset):
    
    if preset not in ['lowlevel', 'music']:
        preset = DEFAULT_SIMILARITY_PRESET
            
    cache_key = "similar-for-sound-%s-%s" % (sound.id, preset)
    
    if settings.DEBUG :
        similar_sounds = False
    else :  
        similar_sounds = cache.get(cache_key)
    
       
    if not similar_sounds:
        try:
            similar_sounds = [x[0] for x in Similarity.search(sound.id, preset, settings.SOUNDS_PER_PAGE)]
            similar_found_p = True
        except:
            similar_sounds = []
            similar_found_p = False
        if similar_found_p:
            cache.set(cache_key, similar_sounds, 60*60*24)
            
    print similar_sounds