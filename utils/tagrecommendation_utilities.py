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

import logging, traceback, settings
from tagrecommendation.client import TagRecommendation
from tagrecommendation.tagrecommendation_settings import TAGRECOMMENDATION_CACHE_TIME, KEY_TAGS, USE_KEYTAGS
from django.core.cache import cache
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
import json
from django.contrib.auth.decorators import login_required
from utils.tags import clean_and_split_tags

logger = logging.getLogger('web')


def get_recommended_tags(input_tags, max_number_of_tags=30):

    cache_key = "recommended-tags-for-%s" % (",".join(sorted(input_tags)))

    # Don't use the cache when we're debugging
    if settings.DEBUG:
        recommended_tags = False
    else:
        recommended_tags = cache.get(cache_key)

    if not recommended_tags:
        try:
            recommended_tags = TagRecommendation.recommend_tags(input_tags)

            if not recommended_tags['tags']:
                recommended_tags['community'] = "-"

            cache.set(cache_key, recommended_tags, TAGRECOMMENDATION_CACHE_TIME)

        except Exception, e:
            logger.debug('Could not get a response from the tagrecommendation service (%s)\n\t%s' % \
                         (e, traceback.format_exc()))
            recommended_tags = False

    return recommended_tags['tags'][:max_number_of_tags], recommended_tags['community']


def get_recommended_tags_view(request):
    if request.is_ajax() and request.method == 'POST':
        input_tags = request.POST.get('input_tags', False)
        if input_tags:
            input_tags = list(clean_and_split_tags(input_tags))
            if len(input_tags) > 0:
                tags, community = get_recommended_tags(input_tags)
                return HttpResponse(json.dumps([tags, community]), mimetype='application/javascript')

    return HttpResponse(json.dumps([[],"-"]), mimetype='application/javascript')


def tag_recommendation_test_page(request):
    return render_to_response('tagrecommendation/test_page.html', locals(), context_instance=RequestContext(request))
