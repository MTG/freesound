from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from sounds.models import Sound

def front_page(request):
    return render_to_response('sounds/home_page.html', {
        "rss_url": settings.FREESOUND_RSS
    }, context_instance=RequestContext(request))
 