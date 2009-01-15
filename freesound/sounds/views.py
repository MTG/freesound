from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from sounds.models import Sound
from forum.models import Post
from django.core.cache import cache

def front_page(request):
    rss_url = settings.FREESOUND_RSS
    pledgie_campaign = 1356

    latest_forum_posts = Post.objects.select_related('author', 'thread', 'thread__forum').all().order_by("-created")[0:10]
    latest_additions = Sound.objects.latest_additions(5)
    
    cache_key = "random_sound"
    random_sound = cache.get(cache_key)
    if not random_sound:
        random_sound = Sound.objects.random()
        cache.set(cache_key, random_sound, 60*60*24)
    
    return render_to_response('index.html', locals(), context_instance=RequestContext(request)) 
 
def sounds(request):
    pass

def sound(request, username, sound_id):
    pass

def pack(request, pack_id):
    pass

def remixed(request):
     pass
 
def random(request):
     pass

def packs(request):
    pass

def packs_for_user(request, username):
    pass

def search(request):
    pass

def for_user(request, username):
    pass

