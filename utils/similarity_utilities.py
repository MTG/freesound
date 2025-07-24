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

import logging
import math
import traceback

from django.conf import settings
from django.core.cache import cache

from similarity.client import Similarity
from similarity.similarity_settings import PRESETS, DEFAULT_PRESET, SIMILARITY_CACHE_TIME
import sounds
from utils.encryption import create_hash

web_logger = logging.getLogger('web')


def get_similar_sounds(sound, preset=DEFAULT_PRESET, num_results=settings.SOUNDS_PER_PAGE, offset=0):

    if preset not in PRESETS:
        preset = DEFAULT_PRESET

    cache_key = "similar-for-sound-%s-%s-%i" % (sound.id, preset, offset)

    # Don't use the cache when we're debugging
    if settings.DEBUG:
        similar_sounds = False
        count = False
    else:
        result = cache.get(cache_key)
        if result:
            similar_sounds = [[int(x[0]), float(x[1])] for x in result['results']]
            count = result['count']
        else:
            similar_sounds = False
            count = False

    if not similar_sounds:
        try:
            result = Similarity.search(sound.id, preset=preset, num_results=num_results, offset=offset)
            similar_sounds = [[int(x[0]), float(x[1])] for x in result['results']]
            count = result['count']
        except Exception as e:
            web_logger.info('Could not get a response from the similarity service (%s)\n\t%s' % \
                             (e, traceback.format_exc()))
            result = False
            similar_sounds = []
            count = 0

        if result:
            cache.set(cache_key, result, SIMILARITY_CACHE_TIME)

    return similar_sounds[0:num_results], count


def api_search(target=None, filter=None, preset=None, metric_descriptor_names=None, num_results=None, offset=None, target_file=None, in_ids=None):

    cache_key = 'api-search-t-{}-f-{}-nr-{}-o-{}'.format(str(target).replace(" ", ""), str(filter).replace(" ", ""), num_results, offset)
    cache_key = hash_cache_key(cache_key)
    note = False
    if in_ids:
        in_ids = ','.join([str(sid) for sid in in_ids if sid])

    # Don't use the cache when we're debugging
    if settings.DEBUG or len(cache_key) >= 250 or in_ids:
        returned_sounds = False
        count = False
    else:
        result = cache.get(cache_key)
        if result:
            returned_sounds = [[int(x[0]), float(x[1])] for x in result['results']]
            count = result['count']
        else:
            returned_sounds = False
            count = False

    if not returned_sounds or target_file:
        if target_file:
            # If there is a file attached, set the file as the target
            target_type = 'file'
            target = None  # If target is given as a file, we set target to None (just in case)
        else:
            # In case there is no file, if the string target represents an integer value, then target is a sound_id, otherwise target is descriptor_values
            if target.isdigit():
                target_type = 'sound_id'
            else:
                target_type = 'descriptor_values'

        result = Similarity.api_search(
            target_type=target_type,
            target=target,
            filter=filter,
            preset=preset,
            metric_descriptor_names=metric_descriptor_names,
            num_results=num_results,
            offset=offset,
            file=target_file,
            in_ids=in_ids
        )

        returned_sounds = [[int(x[0]), float(x[1])] for x in result['results']]
        count = result['count']
        note = result['note']

        if not target_file and not in_ids:
            if len(returned_sounds) > 0 and len(cache_key) < 250 and not settings.DEBUG:
                cache.set(cache_key, result, SIMILARITY_CACHE_TIME)

    return returned_sounds[0:num_results], count, note


def get_sounds_descriptors(sound_ids, descriptor_names, normalization=True, only_leaf_descriptors=False):
    cache_key = "analysis-sound-id-%s-descriptors-%s-normalization-%s"

    cached_data = {}
    # Check if at least some sound analysis data is already on cache
    not_cached_sound_ids = sound_ids[:]
    for id in sound_ids:
        analysis_data = cache.get(hash_cache_key(cache_key % (str(id), ",".join(sorted(descriptor_names)), str(normalization))))
        if analysis_data:
            cached_data[str(id)] = analysis_data
            # remove id form list so it is not included in similarity request
            not_cached_sound_ids.remove(id)
    if not_cached_sound_ids:
        try:
            returned_data = Similarity.get_sounds_descriptors(not_cached_sound_ids, descriptor_names, normalization, only_leaf_descriptors)
        except Exception as e:
            web_logger.info('Something wrong occurred with the "get sound descriptors" request (%s)\n\t%s' %\
                            (e, traceback.format_exc()))
            raise
    else:
        returned_data = {}

    # save sound analysis information in cache
    for key, item in returned_data.items():
        cache.set(hash_cache_key(cache_key % (key, ",".join(sorted(descriptor_names)), str(normalization))),
                  item, SIMILARITY_CACHE_TIME)

    returned_data.update(cached_data)

    return returned_data


def delete_sound_from_gaia(sound_id):
    web_logger.info("Deleting sound from gaia with id %d" % sound_id)
    try:
        Similarity.delete(sound_id)
    except Exception as e:
       web_logger.warning("Could not delete sound from gaia with id %d (%s)" % (sound_id, str(e)))


def hash_cache_key(key):
    return create_hash(key, limit=32)


def get_l2_normalized_vector(vector):
    norm = math.sqrt(sum([v*v for v in vector]))
    if norm > 0:
        vector = [v/norm for v in vector]
    return vector


def get_similarity_search_target_vector(sound_id, analyzer=settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER):
    # If the sound has been analyzed for similarity, returns the vector to be used for similarity search
    sa = sounds.models.SoundAnalysis.objects.filter(sound_id=sound_id, analyzer=analyzer, analysis_status="OK")
    if sa.exists():
        config_options = settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS[analyzer]
        vector_property_name = config_options['vector_property_name']
        sa = sa.first()
        if sa.analysis_data is not None and vector_property_name in sa.analysis_data:
            data = sa.analysis_data
        else:
            data = sa.get_analysis_data_from_file()
        if data is not None:
            vector_raw = data[vector_property_name]
            if vector_raw is not None:
                if config_options['l2_norm']:
                    vector_raw = get_l2_normalized_vector(vector_raw)
                return vector_raw
    return None
