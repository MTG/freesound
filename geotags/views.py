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

import io
import json
import logging
import math
import struct
import urllib.parse

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.clickjacking import xframe_options_exempt
from accounts.models import Profile

from search.views import search_prepare_parameters
from sounds.models import Sound, Pack
from utils.logging_filters import get_client_ip
from utils.search.search_sounds import perform_search_engine_query
from utils.username import redirect_if_old_username_or_404, raise_404_if_user_is_deleted

web_logger = logging.getLogger('web')


def log_map_load(map_type, num_geotags, request):
    web_logger.info('Map load (%s)' % json.dumps({
        'map_type': map_type, 'num_geotags': num_geotags, 'ip': get_client_ip(request)}))


def update_query_params_for_map_query(query_params, preserve_facets=False):
    # Force is_geotagged filter to be present
    if query_params['query_filter']:
        if 'is_geotagged' not in query_params['query_filter']:
            query_params['query_filter'] = query_params['query_filter'] + ' is_geotagged:1'
    else:
        query_params['query_filter'] = 'is_geotagged:1'
    # Force one single page with "all" results, and don't group by pack
    query_params.update({
        'current_page': 1, 
        'num_sounds': settings.MAX_SEARCH_RESULTS_IN_MAP_DISPLAY,
        'group_by_pack': False,
        'only_sounds_with_pack': False,
        'field_list': ['id', 'score', 'geotag']
    })
    if not preserve_facets:
        # No need to compute facets for the bytearray, but it might be needed for the main query
        if 'facets' in query_params:
            del query_params['facets']


def generate_bytearray(sound_queryset_or_list):
    # sounds as bytearray
    packed_sounds = io.BytesIO()
    num_sounds_in_bytearray = 0
    for s in sound_queryset_or_list:
        if type(s) == Sound:
            if not math.isnan(s.geotag.lat) and not math.isnan(s.geotag.lon):
                packed_sounds.write(struct.pack("i", s.id))
                packed_sounds.write(struct.pack("i", int(s.geotag.lat * 1000000)))
                packed_sounds.write(struct.pack("i", int(s.geotag.lon * 1000000)))
                num_sounds_in_bytearray += 1
        elif type(s) == dict:
            try:
                lon, lat = s['geotag'][0].split(' ')
                lat = max(min(float(lat), 90), -90) 
                lon = max(min(float(lon), 180), -180) 
                packed_sounds.write(struct.pack("i", s['id']))
                packed_sounds.write(struct.pack("i", int(lat * 1000000)))
                packed_sounds.write(struct.pack("i", int(lon * 1000000)))
                num_sounds_in_bytearray += 1
            except:
                pass
            
    return packed_sounds.getvalue(), num_sounds_in_bytearray


def geotags_barray(request, tag=None):
    is_embed = request.GET.get("embed", "0") == "1"
    if tag is not None:
        sounds = Sound.objects.select_related('geotag').filter(tags__tag__name__iexact=tag)
        generated_bytearray, num_geotags = generate_bytearray(sounds.exclude(geotag=None).all())
        if num_geotags > 0:
            log_map_load('tag-embed' if is_embed else 'tag', num_geotags, request)
        return HttpResponse(generated_bytearray, content_type='application/octet-stream')
    else:
        all_geotags = cache.get(settings.ALL_GEOTAGS_BYTEARRAY_CACHE_KEY)
        if isinstance(all_geotags, (list, tuple)) and len(all_geotags) == 2:
            cached_bytearray, num_geotags = all_geotags
            log_map_load('all-embed' if is_embed else 'all', num_geotags, request)
            return HttpResponse(cached_bytearray, content_type='application/octet-stream')
        else:
            generated_bytearray, _ = generate_bytearray(Sound.objects.none())
            return HttpResponse(generated_bytearray, content_type='application/octet-stream')


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
@cache_page(60 * 15)
def geotags_for_user_barray(request, username):
    profile = get_object_or_404(Profile, user__username=username)
    is_embed = request.GET.get("embed", "0") == "1"
    results, _ = perform_search_engine_query({
        'query_filter': f'username:"{username}" is_geotagged:1',  # No need to urlencode here as it will happpen somwhere before sending query to solr
        'field_list': ['id', 'score', 'geotag'],
        'num_sounds': profile.num_sounds,
    })
    generated_bytearray, num_geotags = generate_bytearray(results.docs)
    if num_geotags > 0:
        log_map_load('user-embed' if is_embed else 'user', num_geotags, request)
    return HttpResponse(generated_bytearray, content_type='application/octet-stream')


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def geotags_for_user_latest_barray(request, username):
    sounds = Sound.public.filter(user__username__iexact=username).exclude(geotag=None)[0:10]
    generated_bytearray, num_geotags = generate_bytearray(sounds)
    if num_geotags > 0:
        log_map_load('user_latest', num_geotags, request)
    return HttpResponse(generated_bytearray, content_type='application/octet-stream')


def geotags_for_pack_barray(request, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    results, _ = perform_search_engine_query({
        'query_filter': f'grouping_pack:"{pack.id}_{pack.name}" is_geotagged:1',  # No need to urlencode here as it will happpen somwhere before sending query to solr
        'field_list': ['id', 'score', 'geotag'],
        'num_sounds': pack.num_sounds,
    })
    generated_bytearray, num_geotags = generate_bytearray(results.docs)
    if num_geotags > 0:
        log_map_load('pack', num_geotags, request)
    return HttpResponse(generated_bytearray, content_type='application/octet-stream')


def geotag_for_sound_barray(request, sound_id):
    sounds = Sound.objects.filter(id=sound_id).exclude(geotag=None)
    generated_bytearray, num_geotags = generate_bytearray(sounds)
    if num_geotags > 0:
        log_map_load('sound', num_geotags, request)
    return HttpResponse(generated_bytearray, content_type='application/octet-stream')


def geotags_for_query_barray(request):
    results_cache_key = request.GET.get('key', None)
    if results_cache_key is not None:
        # If cache key is present, use it to get the results
        results_docs = cache.get(results_cache_key)
    else:
        # Otherwise, perform a search query to get the results
        query_params, _, _ = search_prepare_parameters(request)
        update_query_params_for_map_query(query_params)
        results, _ = perform_search_engine_query(query_params)
        results_docs = results.docs
    
    generated_bytearray, num_geotags = generate_bytearray(results_docs)
    if num_geotags > 0:
        log_map_load('query', num_geotags, request)
    return HttpResponse(generated_bytearray, content_type='application/octet-stream')


def _get_geotags_query_params(request):
    return {
        'center_lat': request.GET.get('c_lat', None),
        'center_lon': request.GET.get('c_lon', None),
        'zoom': request.GET.get('z', None),
        'username': request.GET.get('username', None),
        'pack': request.GET.get('pack', None),
        'tag': request.GET.get('tag', None),
        'query_params': urllib.parse.unquote(request.GET['qp']) if 'qp' in request.GET else None  # This is used for map embeds based on general queries
    }


def geotags(request, tag=None):
    tvars = _get_geotags_query_params(request)
    if tag is None:
        query_search_page_url = ''
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
        query_search_page_url = reverse('sounds-search') + f'?f=tag:{tag}&mm=1'

    tvars.update({  # Overwrite tag and username query params (if present)
        'tag': tag,
        'username': None,
        'pack': None,
        'url': url,
        'query_search_page_url': query_search_page_url
    })
    return render(request, 'geotags/geotags.html', tvars)


@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def for_user(request, username):
    tvars = _get_geotags_query_params(request)
    tvars.update({  # Overwrite tag and username query params (if present)
        'tag': None,
        'username': request.parameter_user.username,
        'pack': None,
        'sound': None,
        'url': reverse('geotags-for-user-barray', args=[username]),
        'query_search_page_url': reverse('sounds-search') + f'?f=username:{username}&mm=1'
    })
    return render(request, 'geotags/geotags.html', tvars)


@redirect_if_old_username_or_404
def for_sound(request, username, sound_id):
    sound = get_object_or_404(
        Sound.objects.select_related('geotag', 'user'), id=sound_id)
    if sound.user.username.lower() != username.lower() or sound.geotag is None:
        raise Http404
    tvars = _get_geotags_query_params(request)
    tvars.update({
        'tag': None,
        'username': None,
        'pack': None,
        'sound': sound,
        'center_lat': sound.geotag.lat,
        'center_lon': sound.geotag.lon,
        'zoom': sound.geotag.zoom,
        'url': reverse('geotags-for-sound-barray', args=[sound.id]),
        'modal_version': request.GET.get('ajax'),
    })
    if request.GET.get('ajax'):
        # If requested in ajax version, then load using the modal
        return render(request, 'geotags/modal_geotags.html', tvars)
    else:
        # Otherwise load using the normal template
        return render(request, 'geotags/geotags.html', tvars)


@redirect_if_old_username_or_404
def for_pack(request, username, pack_id):
    pack = get_object_or_404(Pack.objects.select_related('user'), id=pack_id)
    tvars = _get_geotags_query_params(request)
    tvars.update({  # Overwrite tag and username query params (if present)
        'tag': None,
        'username': None,
        'pack': pack,
        'sound': None,
        'url': reverse('geotags-for-pack-barray', args=[pack.id]),
        'query_search_page_url': reverse('sounds-search') + f'?f=grouping_pack:"{pack.id}_{urllib.parse.quote(pack.name)}"&mm=1',
        'modal_version': request.GET.get('ajax'),
    })
    if request.GET.get('ajax'):
        # If requested in ajax version, then load using the modal
        return render(request, 'geotags/modal_geotags.html', tvars)
    else:
        # Otherwise load using the normal template
        return render(request, 'geotags/geotags.html', tvars)


def for_query(request):
    tvars = _get_geotags_query_params(request)
    request_parameters_string = request.get_full_path().split('?')[-1]
    q = request.GET.get('q', None)
    f = request.GET.get('f', None)
    query_description = ''
    if q is None and f is None:
        query_description = 'Empty query'
    elif q is not None and f is not None:
        query_description = f'{q} (some filters applied)'
    else:
        if q is not None:
            query_description = q
        if f is not None:
            query_description = f'Empty query with some filtes applied'
    tvars.update({
        'tag': None,
        'username': None,
        'pack': None,
        'sound': None,
        'query_params': request_parameters_string,
        'query_params_encoded': urllib.parse.quote(request_parameters_string),
        'query_search_page_url': reverse('sounds-search') + f'?{request_parameters_string}',
        'query_description': query_description,
        'url': reverse('geotags-for-query-barray') + f'?{request_parameters_string}',
    })
    return render(request, 'geotags/geotags.html', tvars)


@xframe_options_exempt
def embed_iframe(request):
    tvars = _get_geotags_query_params(request)
    tvars.update({
        'm_width': request.GET.get('w', 942),
        'm_height': request.GET.get('h', 600),
        'cluster': request.GET.get('c', 'on') != 'off'
    })
    tvars.update({'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN})
    return render(request, 'embeds/geotags_embed.html', tvars)


def infowindow(request, sound_id):
    try:
        sound = Sound.objects.select_related('user', 'geotag').get(id=sound_id)
    except Sound.DoesNotExist:
        raise Http404
    tvars = {
        'sound': sound,
        'minimal': request.GET.get('minimal', False)
    }
    if request.GET.get('embed', False):
        # When loading infowindow for an embed, use the template for old UI as embeds have not been updated to new UI
        return render(request, 'embeds/geotags_infowindow.html', tvars)
    return render(request, 'geotags/infowindow.html', tvars)
