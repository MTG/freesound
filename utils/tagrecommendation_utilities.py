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

import urllib2
import logging, traceback
from django.conf import settings
from tagrecommendation.client import TagRecommendation
from tagrecommendation.client.client_fslabs import NewTagRecommendation
from tagrecommendation.tagrecommendation_settings import TAGRECOMMENDATION_CACHE_TIME
from django.core.cache import cache
from django.shortcuts import render
from django.template import RequestContext
from django.http import HttpResponse
from hashlib import md5
import json
from django.contrib.auth.decorators import login_required
from utils.tags import clean_and_split_tags
from math import ceil

logger = logging.getLogger('web')


def get_recommended_tags(input_tags, max_number_of_tags=30):

    hashed_tags = md5(",".join(sorted(input_tags)))
    cache_key = "recommended-tags-for-%s" % (hashed_tags.hexdigest())

    recommended_tags = False
    # Don't use the cache when we're debugging
    if not settings.DEBUG:
        recommended_tags = cache.get(cache_key)

    if not recommended_tags:
        recommended_tags = TagRecommendation.recommend_tags(input_tags)

        if not recommended_tags['tags']:
            recommended_tags['community'] = "-"

        cache.set(cache_key, recommended_tags, TAGRECOMMENDATION_CACHE_TIME)

    return recommended_tags['tags'][:max_number_of_tags], recommended_tags['community']


def get_recommended_tags_view(request):
    if request.is_ajax() and request.method == 'POST':
        input_tags = request.POST.get('input_tags', False)
        if input_tags:
            input_tags = list(clean_and_split_tags(input_tags))
            if len(input_tags) > 0:
                try:
                    tags, community = get_recommended_tags(input_tags)
                    return HttpResponse(json.dumps([tags, community]), content_type='application/javascript')
                except urllib2.URLError as e:
                    logger.error('Could not get a response from the tagrecommendation service (%s)\n\t%s' % \
                         (e, traceback.format_exc()))
                    return HttpResponseUnavailabileError()

    return HttpResponse(json.dumps([[],"-"]), content_type='application/javascript')


def get_id_of_last_indexed_sound():
    try:
        result = TagRecommendation.get_last_indexed_id()
        return result

    except Exception as e:
        return -1


def post_sounds_to_tagrecommendation_service(sound_qs):
    data_to_post = []
    N_SOUNDS_PER_CALL = 10
    total_calls = int(ceil(float(len(sound_qs))/N_SOUNDS_PER_CALL))
    print "Sending recommendation data..."
    idx = 1
    for count, sound in enumerate(sound_qs):
        data_to_post.append(
            (sound.id, list(sound.tags.select_related("tag").values_list('tag__name', flat=True)))
        )
        if (count + 1) % N_SOUNDS_PER_CALL == 0:
            ids = [element[0] for element in data_to_post]
            tagss = [element[1] for element in data_to_post]
            print "\tSending group of sounds %i of %i (%i sounds)" % (idx, total_calls, len(ids))
            idx += 1
            TagRecommendation.add_to_index(ids, tagss)
            data_to_post = []

    if data_to_post:
        ids = [element[0] for element in data_to_post]
        tagss = [element[1] for element in data_to_post]
        print "\tSending group of sounds %i of %i (%i sounds)" % (idx, total_calls, len(ids))
        TagRecommendation.add_to_index(ids, tagss)

    print "Finished!"


### Views for new tag recommendation interface experiment
def new_tagrecommendation_interface_instructions(request):
    return render(request, 'tagrecommendation/new_interface_instructions.html', locals())


def get_recommended_tags_view_new(request):
    if request.is_ajax() and request.method == 'POST':
        input_tags = request.POST.get('input_tags', False)
        category = request.POST.get('category', False)
        if category:
            result = NewTagRecommendation.recommend_tags_category(input_tags, category)
        else:
            result = NewTagRecommendation.recommend_tags(input_tags)
        return HttpResponse(json.dumps(result), content_type='application/javascript')

    return HttpResponse(json.dumps({'tags':[], 'audio_category':None}), content_type='application/javascript')


def get_recommended_categories_view(request):
    if request.is_ajax() and request.method == 'POST':
        input_tags = request.POST.get('input_tags', False)
        result = NewTagRecommendation.recommend_categories(input_tags)
        categories = [str(category) for category in result['categories']]
        return HttpResponse(json.dumps(categories), content_type='application/javascript')

    return HttpResponse(json.dumps([]), content_type='application/javascript')


def get_all_categories_view(request):
    if request.is_ajax() and request.method == 'POST':
        result = NewTagRecommendation.all_tag_categories()
        categories = [str(category) for category in result['categories']]
        return HttpResponse(json.dumps(categories), content_type='application/javascript')

    return HttpResponse(json.dumps([]), content_type='application/javascript')


class HttpResponseUnavailabileError(HttpResponse):
    status_code = 503
