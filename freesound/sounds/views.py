from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from sounds.models import Sound
from utils.rssgrabber import grab

def front_page(request):
    rss = grab("http://www.freesound.org/blog/?feed=rss2")
    return render_to_response('sounds/home_page.html', {"rss":rss}, context_instance=RequestContext(request))
 