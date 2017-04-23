#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

import cStringIO
import struct
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.template import RequestContext
from sounds.models import Sound
from django.views.decorators.cache import cache_page
from django.contrib.auth.models import User
import json
import math


def generate_bytearray(sound_queryset):
    # sounds as bytearray
    packed_sounds = cStringIO.StringIO()
    for s in sound_queryset:
        if not math.isnan(s.geotag.lat) and not math.isnan(s.geotag.lon):
            packed_sounds.write(struct.pack("i", s.id))
            packed_sounds.write(struct.pack("i", int(s.geotag.lat*1000000)))
            packed_sounds.write(struct.pack("i", int(s.geotag.lon*1000000)))

    return HttpResponse(packed_sounds.getvalue(), content_type='application/octet-stream')


@cache_page(60 * 15)
def geotags_barray(request, tag=None):
    sounds = Sound.objects.select_related('geotag')
    if tag:
        sounds = sounds.filter(tags__tag__name=tag)
    return generate_bytearray(sounds.exclude(geotag=None).all())


def geotags_box_barray(request):
    box = request.GET.get("box","-180,-90,180,90")
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

        return generate_bytearray(sounds)
    except ValueError:
        raise Http404


@cache_page(60 * 15)
def geotags_for_user_barray(request, username):
    sounds = Sound.public.select_related('geotag').filter(user__username__iexact=username).exclude(geotag=None)
    return generate_bytearray(sounds)


#@cache_page(60 * 15)
def geotags_for_user_latest_barray(request, username):
    sounds = Sound.public.filter(user__username__iexact=username).exclude(geotag=None)[0:10]
    return generate_bytearray(sounds)


#@cache_page(60 * 15)
def geotags_for_pack_barray(request, pack_id):
    sounds = Sound.public.select_related('geotag').filter(pack__id=pack_id).exclude(geotag=None)
    return generate_bytearray(sounds)


def geotags(request, tag=None):
    google_api_key = settings.GOOGLE_API_KEY
    for_user = None
    tvars = {
        'google_api_key': google_api_key,
        'for_user': for_user
    }
    return render(request, 'geotags/geotags.html', tvars)


def geotags_box(request):
    m_width = request.GET.get("w",900)
    m_height = request.GET.get("h",600)
    clusters = request.GET.get("c","on")
    center_lat = request.GET.get("c_lat",None)
    center_lon = request.GET.get("c_lon",None)
    zoom = request.GET.get("z",None)
    username = request.GET.get("username",None)

    google_api_key = settings.GOOGLE_API_KEY
    tvars = {
        'google_api_key': google_api_key,
        'm_width': m_width,
        'm_height': m_height,
        'clusters': clusters,
        'center_lat': center_lat,
        'center_lon': center_lon,
        'zoom': zoom,
        'username': username
    }
    return render(request, 'geotags/geotags_box.html', tvars)



def for_user(request, username):
    for_user = None
    try:
        for_user = User.objects.get(username__iexact=username)
    except User.DoesNotExist: #@UndefinedVariable
        raise Http404
    tvars = {
        'google_api_key': settings.GOOGLE_API_KEY,
        'tag': None,
        'for_user': for_user
    }
    return render(request, 'geotags/geotags.html', tvars)


def infowindow(request, sound_id):
    sound = None
    try:
        sound = Sound.objects.select_related('user', 'geotag').get(id=sound_id)
    except Sound.DoesNotExist: #@UndefinedVariable
        raise Http404

    tvars = {
        'sound': sound
    }
    return render(request, 'geotags/infowindow.html', tvars)


def embed_iframe(request):
    m_width = request.GET.get("w",900)
    m_height = request.GET.get("h",600)
    clusters = request.GET.get("c","on")
    center_lat = request.GET.get("c_lat",None)
    center_lon = request.GET.get("c_lon",None)
    zoom = request.GET.get("z",None)
    username = request.GET.get("username",None)

    tvars = {
        'm_width': m_width,
        'm_height': m_height,
        'clusters': clusters,
        'center_lat': center_lat,
        'center_lon': center_lon,
        'zoom': zoom,
        'username': username,
        'google_api_key': settings.GOOGLE_API_KEY
    }
    return render(request, 'geotags/geotags_box_iframe.html', tvars)
