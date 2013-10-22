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

import settings, traceback, logging
from sounds.models import Sound
from django.core.cache import cache
from similarity.client import Similarity
from similarity.similarity_settings import PRESETS, DEFAULT_PRESET, SIMILAR_SOUNDS_TO_CACHE, SIMILARITY_CACHE_TIME

logger = logging.getLogger('web')

def get_similar_sounds(sound, preset = DEFAULT_PRESET, num_results = settings.SOUNDS_PER_PAGE ):

    if preset not in PRESETS:
        preset = DEFAULT_PRESET

    cache_key = "similar-for-sound-%s-%s" % (sound.id, preset)

    # Don't use the cache when we're debugging
    if settings.DEBUG:
        similar_sounds = False
    else:
        similar_sounds = cache.get(cache_key)

    if not similar_sounds:
        try:
            similar_sounds = [ [int(x[0]),float(x[1])] for x in Similarity.search(sound.id, preset = preset, num_results = SIMILAR_SOUNDS_TO_CACHE)]
        except Exception, e:
            logger.debug('Could not get a response from the similarity service (%s)\n\t%s' % \
                         (e, traceback.format_exc()))
            similar_sounds = []

        if len(similar_sounds) > 0:
            cache.set(cache_key, similar_sounds, SIMILARITY_CACHE_TIME)

    return similar_sounds[0:num_results]


def query_for_descriptors(target, filter, num_results = settings.SOUNDS_PER_PAGE):

    cache_key = "content-based-search-t-%s-f-%s-nr-%s" % (target.replace(" ",""),filter.replace(" ",""),num_results)

    # Don't use the cache when we're debugging
    if settings.DEBUG:
        returned_sounds = False
    else:
        returned_sounds = cache.get(cache_key)

    if not returned_sounds:
        try:
            returned_sounds = [ [int(x[0]),float(x[1])] for x in Similarity.query(target, filter, num_results)]
        except Exception, e:
            logger.info('Something wrong occurred with the "query for descriptors" request (%s)\n\t%s' %\
                         (e, traceback.format_exc()))
            raise Exception(e)

        if len(returned_sounds) > 0:# and returned_sounds[0] != -999:
            cache.set(cache_key, returned_sounds, SIMILARITY_CACHE_TIME)

    return returned_sounds[0:num_results]


def get_sounds_descriptors(sound_ids, descriptor_names, normalization=True):

    cache_key = "analysis-sound-id-%s-descriptors-%s"

    cached_data = {}
    # Check if at least some sound analysis data is already on cache
    not_cached_sound_ids = sound_ids[:]
    for id in sound_ids:
        analysis_data = cache.get(cache_key % (str(id), ",".join(sorted(descriptor_names))))
        if analysis_data:
            cached_data[unicode(id)] = analysis_data
            # remove id form list so it is not included in similarity request
            not_cached_sound_ids.remove(id)
    try:
        returned_data = Similarity.get_sounds_descriptors(not_cached_sound_ids, descriptor_names, normalization)
    except Exception, e:
        logger.info('Something wrong occurred with the "get sound descriptors" request (%s)\n\t%s' %\
                     (e, traceback.format_exc()))
        raise Exception(e)

    # save sound analysis information in cache
    for key, item in returned_data.items():
        cache.set(cache_key % (key, ",".join(sorted(descriptor_names))),
                  item, SIMILARITY_CACHE_TIME)

    returned_data.update(cached_data)
    return returned_data