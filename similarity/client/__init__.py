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

from similarity.similarity_settings import SIMILARITY_ADDRESS, SIMILARITY_PORT, SIMILARITY_INDEXING_SERVER_PORT
import json
import urllib2

_BASE_URL                     = 'http://%s:%i/similarity/' % (SIMILARITY_ADDRESS, SIMILARITY_PORT)
_BASE_INDEXING_SERVER_URL     = 'http://%s:%i/similarity/' % (SIMILARITY_ADDRESS, SIMILARITY_INDEXING_SERVER_PORT)
_URL_ADD_POINT                = 'add_point/'
_URL_DELETE_POINT             = 'delete_point/'
_URL_GET_DESCRIPTOR_NAMES     = 'get_descriptor_names/'
_URL_GET_ALL_SOUND_IDS        = 'get_all_point_names/'
_URL_CONTAINS_POINT           = 'contains/'
_URL_NNSEARCH                 = 'nnsearch/'
_URL_API_SEARCH               = 'api_search/'
_URL_SOUNDS_DESCRIPTORS       = 'get_sounds_descriptors/'
_URL_SAVE                     = 'save/'
_URL_RELOAD_GAIA_WRAPPER      = 'reload_gaia_wrapper/'
_URL_CLEAR_MEMORY             = 'clear_memory/'


class SimilarityException(Exception):
    status_code = None

    def __init__(self, *args, **kwargs):
        super(SimilarityException, self).__init__(*args)
        self.status_code = kwargs['status_code']


def _get_url_as_json(url, data=None, timeout=None):
    kwargs = dict()
    if data is not None:
        kwargs['data'] = data
    if timeout is not None:
        kwargs['timeout'] = timeout
    f = urllib2.urlopen(url.replace(" ", "%20"), **kwargs)
    resp = f.read()
    return json.loads(resp)


def _result_or_exception(result):
    if not result['error']:
        return result['result']
    else:
        if 'status_code' in result.keys():
            raise SimilarityException(result['result'], status_code=result['status_code'])
        else:
            raise SimilarityException(result['result'], status_code=500)


class Similarity():

    @classmethod
    def search(cls, sound_id, num_results = None, preset = None, offset = None):
        url = _BASE_URL + _URL_NNSEARCH + '?' + 'sound_id=' + str(sound_id)
        if num_results:
            url += '&num_results=' + str(num_results)
        if preset:
            url += '&preset=' + preset
        if offset:
            url += '&offset=' + str(offset)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def api_search(cls, target_type=None, target=None, filter=None, preset=None, metric_descriptor_names=None, num_results=None, offset=None, file=None, in_ids=None):
        url = _BASE_URL + _URL_API_SEARCH + '?'
        if target_type:
            url += '&target_type=' + str(target_type)
        if target:
            url += '&target=' + str(target)
        if filter:
            url += '&filter=' + str(filter)
        if preset:
            url += '&preset=' + str(preset)
        if metric_descriptor_names:
            url += '&metric_descriptor_names=' + str(metric_descriptor_names)
        if num_results:
            url += '&num_results=' + str(num_results)
        if offset:
            url += '&offset=' + str(offset)
        if in_ids:
            url += '&in_ids=' + str(in_ids)

        j = _get_url_as_json(url, data=file)
        r = _result_or_exception(j)

        return r

    @classmethod
    def add(cls, sound_id, yaml_path):
        url = _BASE_URL + _URL_ADD_POINT + '?' + 'sound_id=' + str(sound_id) + '&location=' + str(yaml_path)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def add_to_indeixing_server(cls, sound_id, yaml_path):
        url = _BASE_INDEXING_SERVER_URL + _URL_ADD_POINT + '?' + 'sound_id=' + str(sound_id) + '&location=' + str(yaml_path)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def get_all_sound_ids(cls):
        url = _BASE_URL + _URL_GET_ALL_SOUND_IDS
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def get_descriptor_names(cls):
        url = _BASE_URL + _URL_GET_DESCRIPTOR_NAMES
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def delete(cls, sound_id):
        url = _BASE_URL + _URL_DELETE_POINT + '?' + 'sound_id=' + str(sound_id)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def contains(cls, sound_id):
        url = _BASE_URL + _URL_CONTAINS_POINT + '?' + 'sound_id=' + str(sound_id)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def save(cls, filename = None):
        url = _BASE_URL + _URL_SAVE
        if filename:
            url += '?' + 'filename=' + str(filename)
        return _result_or_exception(_get_url_as_json(url, timeout=60 * 5))

    @classmethod
    def save_indexing_server(cls, filename = None):
        url = _BASE_INDEXING_SERVER_URL + _URL_SAVE
        if filename:
            url += '?' + 'filename=' + str(filename)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def clear_indexing_server_memory(cls):
        url = _BASE_INDEXING_SERVER_URL + _URL_CLEAR_MEMORY
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def reload_indexing_server_gaia_wrapper(cls):
        url = _BASE_INDEXING_SERVER_URL + _URL_RELOAD_GAIA_WRAPPER
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def get_sounds_descriptors(cls, sound_ids, descriptor_names=None, normalization=True, only_leaf_descriptors=False):
        url = _BASE_URL + _URL_SOUNDS_DESCRIPTORS + '?' + 'sound_ids=' + ','.join([str(sound_id) for sound_id in sound_ids])
        if descriptor_names:
            url += '&descriptor_names=' + ','.join(descriptor_names)
        if normalization:
            url += '&normalization=1'
        if only_leaf_descriptors:
            url += '&only_leaf_descriptors=1'

        return _result_or_exception(_get_url_as_json(url))
