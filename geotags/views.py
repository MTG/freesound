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
import math
import struct

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.clickjacking import xframe_options_exempt

from sounds.models import Sound
from utils.frontend_handling import render
from utils.username import redirect_if_old_username_or_404, raise_404_if_user_is_deleted


def generate_bytearray(sound_queryset):
    # sounds as bytearray
    packed_sounds = cStringIO.StringIO()
    for s in sound_queryset:
        if not math.isnan(s.geotag.lat) and not math.isnan(s.geotag.lon):
            packed_sounds.write(struct.pack("i", s.id))
            packed_sounds.write(struct.pack("i", int(s.geotag.lat*1000000)))
            packed_sounds.write(struct.pack("i", int(s.geotag.lon*1000000)))

    return HttpResponse(packed_sounds.getvalue(), content_type='application/octet-stream')


def geotags_barray(request, tag=None):
    if tag is not None:
        sounds = Sound.objects.select_related('geotag').filter(tags__tag__name__iexact=tag)
        return generate_bytearray(sounds.exclude(geotag=None).all())
    else:
        cached_bytearay = cache.get(settings.ALL_GEOTAGS_BYTEARRAY_CACHE_KEY)
        if cached_bytearay is None:
            return generate_bytearray(Sound.objects.none())
        else:
            return cached_bytearay


def geotags_box_barray(request):
    box = request.GET.get("box", "-180,-90,180,90")
    try:
        min_lat, min_lon, max_lat, max_lon = box.split(",")
        qs = Sound.objects.select_related("geotag").exclude(geotag=None).filter(moderation_state="OK", processing_state="OK")
        sounds = []
        if min_lat <= max_lat and min_lon <= max_lon:
            sounds = qs.filter(geotag__lat__range=(min_lat, max_lat)).filter(geotag__lon__range=(min_lon, max_lon))
        elif min_lat > max_lat and min_lon <= max_lon:
            sounds = qs.exclude(geotag__lat__range=(max_lat, min_lat)).filter(geotag__lon__range=(min_lon, max_lon))
        elif min_lat <= max_lat and min_lon > max_lon:
            sounds = qs.filter(geotag__lat__range=(min_lat, max_lat)).exclude(geotag__lon__range=(max_lon, min_lon))
        elif min_lat > max_lat and min_lon > max_lon:
            sounds = qs.exclude(geotag__lat__range=(max_lat, min_lat)).exclude(geotag__lon__range=(max_lon, min_lon))

        return generate_bytearray(sounds)
    except ValueError:
        raise Http404


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
@cache_page(60 * 15)
def geotags_for_user_barray(request, username):
    sounds = Sound.public.select_related('geotag').filter(user__username__iexact=username).exclude(geotag=None)
    return generate_bytearray(sounds)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def geotags_for_user_latest_barray(request, username):
    sounds = Sound.public.filter(user__username__iexact=username).exclude(geotag=None)[0:10]
    return generate_bytearray(sounds)


def geotags_for_pack_barray(request, pack_id):
    sounds = Sound.public.select_related('geotag').filter(pack__id=pack_id).exclude(geotag=None)
    return generate_bytearray(sounds)


def geotag_for_sound_barray(request, sound_id):
    sounds = Sound.objects.filter(id=sound_id).exclude(geotag=None)
    return generate_bytearray(sounds)


def _get_geotags_query_params(request):
    return {
        'center_lat': request.GET.get('c_lat', None),
        'center_lon': request.GET.get('c_lon', None),
        'zoom': request.GET.get('z', None),
        'username': request.GET.get('username', None),
        'tag': request.GET.get('tag', None),
    }


def geotags(request, tag=None):
    tvars = _get_geotags_query_params(request)
    if tag is None:
        url = reverse('geotags-barray')
        # If "all geotags map" and no lat/lon/zoom is indicated, center map so whole world is visible
        if tvars['center_lat'] is None:
            tvars['center_lat'] = 24
        if tvars['center_lon'] is None:
            tvars['center_lon'] = 20
        if tvars['zoom'] is None:
            tvars['zoom'] = 2
    else:
        url = reverse('geotags-barray', args=[tag])

    tvars.update({  # Overwrite tag and username query params (if present)
        'tag': tag,
        'username': None,
        'url': url,
    })
    return render(request, 'geotags/geotags.html', tvars)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def for_user(request, username):
    tvars = _get_geotags_query_params(request)
    tvars.update({  # Overwrite tag and username query params (if present)
        'tag': None,
        'username': request.parameter_user.username,
        'url': reverse('geotags-for-user-barray', args=[username]),
    })
    return render(request, 'geotags/geotags.html', tvars)


def geotags_box(request):
    # This view works the same as "geotags" but it takes the username/tag parameter from query parameters and
    # onyl gets the geotags for a specific bounding box specified via hash parameters.
    # Currently we are only keeping this as legacy because it is not used anymore but there might still be
    # links pointing to it.
    tvars = _get_geotags_query_params(request)
    return render(request, 'geotags/geotags.html', tvars)


@xframe_options_exempt
def embed_iframe(request):
    tvars = _get_geotags_query_params(request)
    tvars.update({
        'm_width': request.GET.get('w', 942),
        'm_height': request.GET.get('h', 600),
        'cluster': request.GET.get('c', 'on') != 'off',
        'media_url': settings.MEDIA_URL,
    })
    return render(request, 'geotags/geotags_box_iframe.html', tvars)


def infowindow(request, sound_id):
    try:
        sound = Sound.objects.select_related('user', 'geotag').get(id=sound_id)
    except Sound.DoesNotExist:
        raise Http404

    tvars = {
        'sound': sound,
        'minimal': request.GET.get('minimal', False)
    }
    return render(request, 'geotags/infowindow.html', tvars)
