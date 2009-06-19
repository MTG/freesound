from django.conf import settings, settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from sounds.models import Sound


def geotags(request):
    pass

def for_user(request, username):
    pass

def infowindow(request, sound_id):
    try:
        sound = Sound.objects.select_related('user', 'geotag').get(id=sound_id)
    except Sound.DoesNotExist:
        raise Http404
    
    return render_to_response('geotags/infowindow.html', locals(), context_instance=RequestContext(request))