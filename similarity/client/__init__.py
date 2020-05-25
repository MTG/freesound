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

import requests
from django.conf import settings

_URL_ADD_POINT = 'add_point/'
_URL_DELETE_POINT = 'delete_point/'
_URL_GET_DESCRIPTOR_NAMES = 'get_descriptor_names/'
_URL_GET_ALL_SOUND_IDS = 'get_all_point_names/'
_URL_CONTAINS_POINT = 'contains/'
_URL_NNSEARCH = 'nnsearch/'
_URL_API_SEARCH = 'api_search/'
_URL_SOUNDS_DESCRIPTORS = 'get_sounds_descriptors/'
_URL_SAVE = 'save/'
_URL_RELOAD_GAIA_WRAPPER = 'reload_gaia_wrapper/'
_URL_CLEAR_MEMORY = 'clear_memory/'


class SimilarityException(Exception):
    status_code = None

    def __init__(self, *args, **kwargs):
        super(SimilarityException, self).__init__(*args)
        self.status_code = kwargs['status_code']


def _get_url_as_json(url, data=None, timeout=None):
    # TODO: (requests): If no timeout is specified explicitly, requests do not time out.
    kwargs = dict()
    if data is not None:
        kwargs['data'] = data
    if timeout is not None:
        kwargs['timeout'] = timeout
    r = requests.get(url.replace(" ", "%20"), **kwargs)
    r.raise_for_status()
    return r.json()


def _result_or_exception(result):
    if not result['error']:
        return result['result']
    else:
        if 'status_code' in result.keys():
            raise SimilarityException(result['result'], status_code=result['status_code'])
        else:
            raise SimilarityException(result['result'], status_code=500)


class Similarity(object):

    def __init__(self, host):
        self.base_url = 'http://%s/similarity/' % host

    def search(self, sound_id, num_results = None, preset = None, offset = None):
        url = self.base_url + _URL_NNSEARCH + '?' + 'sound_id=' + str(sound_id)
        if num_results:
            url += '&num_results=' + str(num_results)
        if preset:
            url += '&preset=' + preset
        if offset:
            url += '&offset=' + str(offset)
        return _result_or_exception(_get_url_as_json(url))

    def api_search(self, target_type=None, target=None, filter=None, preset=None, metric_descriptor_names=None,
                   num_results=None, offset=None, file=None, in_ids=None):
        url = self.base_url + _URL_API_SEARCH + '?'
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

    def add(self, sound_id, yaml_path):
        url = self.base_url + _URL_ADD_POINT + '?' + 'sound_id=' + str(sound_id) + '&location=' + str(yaml_path)
        return _result_or_exception(_get_url_as_json(url))

    def get_all_sound_ids(self):
        url = self.base_url + _URL_GET_ALL_SOUND_IDS
        return _result_or_exception(_get_url_as_json(url))

    def get_descriptor_names(self):
        url = self.base_url + _URL_GET_DESCRIPTOR_NAMES
        return _result_or_exception(_get_url_as_json(url))

    def delete(self, sound_id):
        url = self.base_url + _URL_DELETE_POINT + '?' + 'sound_id=' + str(sound_id)
        return _result_or_exception(_get_url_as_json(url))

    def save(self, filename=None):
        url = self.base_url + _URL_SAVE
        if filename:
            url += '?' + 'filename=' + str(filename)
        return _result_or_exception(_get_url_as_json(url, timeout=60 * 5))

    def get_sounds_descriptors(self, sound_ids, descriptor_names=None, normalization=True, only_leaf_descriptors=False):
        url = self.base_url + _URL_SOUNDS_DESCRIPTORS + '?' + 'sound_ids=' + ','.join(
            [str(sound_id) for sound_id in sound_ids])
        if descriptor_names:
            url += '&descriptor_names=' + ','.join(descriptor_names)
        if normalization:
            url += '&normalization=1'
        if only_leaf_descriptors:
            url += '&only_leaf_descriptors=1'

        return _result_or_exception(_get_url_as_json(url))


similarity_client = Similarity(settings.SIMILARITY_ADDRESS)
indexing_similarity_client = Similarity(settings.INDEXING_SIMILARITY_ADDRESS)
