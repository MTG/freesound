from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from sounds.models import Sound
from django.views.decorators.cache import cache_page
from django.contrib.auth.models import User
import json


def generate_json(sound_queryset):
    sounds_data = []

    for sound in sound_queryset:
        sounds_data.append([sound.id, sound.geotag.lat, sound.geotag.lon])

    return HttpResponse(json.dumps(sounds_data))

@cache_page(60 * 15)
def geotags_json(request, tag=None):
    if tag:
        sounds = Sound.objects.select_related('geotag').filter(tags__tag__name=tag).exclude(geotag=None)
    else:
        sounds = Sound.objects.select_related('geotag').all().exclude(geotag=None)

    return generate_json(sounds)

def geotags_box_json(request):    
    
    box = request.GET.get("box","-180,-90,180,90")
    print "geotags_box_json ", box
    try:
        min_lat, min_lon, max_lat, max_lon = box.split(",")  
        qs = Sound.objects.select_related("geotag").exclude(geotag=None).filter(moderation_state="OK", processing_state="OK")        
        if min_lat <= max_lat and min_lon <= max_lon:
            sounds = qs.filter(geotag__lat__range=(min_lat,max_lat)).filter(geotag__lon__range=(min_lon,max_lon))
        elif min_lat > max_lat and min_lon <= max_lon:
            sounds = qs.exclude(geotag__lat__range=(max_lat,min_lat)).filter(geotag__lon__range=(min_lon,max_lon))
        elif min_lat <= max_lat and min_lon > max_lon:
            sounds =qs.filter(geotag__lat__range=(min_lat,max_lat)).exclude(geotag__lon__range=(max_lon,min_lon))
        elif min_lat > max_lat and min_lon > max_lon:
            sounds = qs.exclude(geotag__lat__range=(max_lat,min_lat)).exclude(geotag__lon__range=(max_lon,min_lon))        
        return generate_json(sounds)
    except:
        raise Http404
    
@cache_page(60 * 15)
def geotags_for_user_json(request, username):
    sounds = Sound.objects.select_related('user', 'geotag').filter(user__username__iexact=username).exclude(geotag=None)
    return generate_json(sounds)

#@cache_page(60 * 15)
def geotags_for_user_latest_json(request, username):
    sounds = Sound.public.filter(user__username__iexact=username).exclude(geotag=None)[0:10]
    return generate_json(sounds)

#@cache_page(60 * 15)
def geotags_for_pack_json(request, pack_id):
    sounds = Sound.public.select_related('license', 'pack', 'geotag', 'user', 'user__profile').filter(pack__id=pack_id).exclude(geotag=None)
    return generate_json(sounds)

def geotags(request, tag=None):
    google_api_key = settings.GOOGLE_API_KEY
    for_user = None
    return render_to_response('geotags/geotags.html', locals(), context_instance=RequestContext(request))

def geotags_box(request):
    m_width = request.GET.get("w",900)
    m_height = request.GET.get("h",600)
    clusters = request.GET.get("c","on")
    center_lat = request.GET.get("c_lat",None)
    center_lon = request.GET.get("c_lon",None)
    zoom = request.GET.get("z",None)
    
    google_api_key = settings.GOOGLE_API_KEY
    return render_to_response('geotags/geotags_box.html', locals(), context_instance=RequestContext(request))


def for_user(request, username):
    try:
        for_user = User.objects.get(username__iexact=username)
    except User.DoesNotExist: #@UndefinedVariable
        raise Http404
    google_api_key = settings.GOOGLE_API_KEY
    tag = None
    return render_to_response('geotags/geotags.html', locals(), context_instance=RequestContext(request))


def infowindow(request, sound_id):
    try:
        sound = Sound.objects.select_related('user', 'geotag').get(id=sound_id)
    except Sound.DoesNotExist: #@UndefinedVariable
        raise Http404

    return render_to_response('geotags/infowindow.html', locals(), context_instance=RequestContext(request))
    
def embed_iframe(request):
    m_width = request.GET.get("w",900)
    m_height = request.GET.get("h",600)
    clusters = request.GET.get("c","on")
    center_lat = request.GET.get("c_lat",None)
    center_lon = request.GET.get("c_lon",None)
    zoom = request.GET.get("z",None)
    
    google_api_key = settings.GOOGLE_API_KEY
    return render_to_response('geotags/geotags_box_iframe.html', locals(), context_instance=RequestContext(request))
