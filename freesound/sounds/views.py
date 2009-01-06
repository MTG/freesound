from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from sounds.models import Sound

def front_page(request):
    return render_to_response('index.html', {
        "rss_url": settings.FREESOUND_RSS
    }, context_instance=RequestContext(request)) 
 
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

