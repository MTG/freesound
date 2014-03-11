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

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from sounds.models import Sound
from django.views.decorators.cache import cache_page
from django.contrib.auth.models import User
import json

"""
SQL queries in this file are done manually in order to force an INNER JOIN,
since Django insists on doing an OUTER LEFT JOIN, which is too slow.
The equivalent Django query is also provided for each raw query.
"""

geoquery = """SELECT sounds_sound.id,
                     geotags_geotag.lat,
                     geotags_geotag.lon
                FROM sounds_sound
                     %(join)s
          INNER JOIN geotags_geotag
                  ON (sounds_sound.geotag_id = geotags_geotag.id)
               WHERE sounds_sound.processing_state = 'OK'
                 AND sounds_sound.moderation_state = 'OK'
                     %(where)s
            ORDER BY sounds_sound.created DESC
                     %(end)s"""

def generate_json(sound_queryset):
    # When using Django Sound queries:
    #sounds_data = [[s.id, s.geotag.lat, s.geotag.lon] for s in sound_queryset]

    sounds_data = [[s.id, s.lat, s.lon] for s in sound_queryset]

    return HttpResponse(json.dumps(sounds_data), mimetype="application/json")

@cache_page(60 * 15)
def geotags_json(request, tag=None):
    if tag:
        #sounds = Sound.objects.select_related('geotag').filter(tags__tag__name=tag).exclude(geotag=None)
        join = """INNER JOIN "tags_taggeditem"
                           ON ("sounds_sound"."id" = "tags_taggeditem"."object_id")
                   INNER JOIN "tags_tag"
                           ON ("tags_taggeditem"."tag_id" = "tags_tag"."id")"""
        where = """AND "tags_tag"."name" = %s"""
        q = geoquery % {"join": join, "where": where, "end": ""}
        sounds = Sound.objects.raw(q, [tag])
    else:
        #sounds = Sound.public.select_related('geotag').all().exclude(geotag=None)
        q = geoquery % {"join": "", "where": "", "end": ""}
        sounds = Sound.objects.raw(q)

    return generate_json(sounds)

def geotags_box_json(request):    
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
        return generate_json(sounds)
    except ValueError:
        raise Http404
    
@cache_page(60 * 15)
def geotags_for_user_json(request, username):
    #sounds = Sound.public.select_related('geotag').filter(user__username__iexact=username).exclude(geotag=None)
    join = """INNER JOIN "auth_user"
                      ON ("sounds_sound"."user_id" = "auth_user"."id")"""
    where = """AND UPPER("auth_user"."username"::text) = UPPER(%s)"""
    q = geoquery % {"join": join, "where": where, "end": ""}
    sounds = Sound.objects.raw(q, [username])
    return generate_json(sounds)

#@cache_page(60 * 15)
def geotags_for_user_latest_json(request, username):
    #sounds = Sound.public.filter(user__username__iexact=username).exclude(geotag=None)[0:10]
    join = """INNER JOIN "auth_user"
                      ON ("sounds_sound"."user_id" = "auth_user"."id")"""
    where = """AND UPPER("auth_user"."username"::text) = UPPER(%s)"""
    end = "LIMIT 10"
    q = geoquery % {"join": join, "where": where, "end": end}
    sounds = Sound.objects.raw(q, [username])
    return generate_json(sounds)

#@cache_page(60 * 15)
def geotags_for_pack_json(request, pack_id):
    #sounds = Sound.public.select_related('geotag').filter(pack__id=pack_id).exclude(geotag=None)
    where = "AND pack_id = %s"
    q = geoquery % {"join": "", "where": where, "end": ""}
    sounds = Sound.objects.raw(q, [pack_id])
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
    username = request.GET.get("username",None)
    
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
    username = request.GET.get("username",None)
    
    google_api_key = settings.GOOGLE_API_KEY
    return render_to_response('geotags/geotags_box_iframe.html', locals(), context_instance=RequestContext(request))
