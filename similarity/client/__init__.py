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

from similarity.similarity_settings import SIMILARITY_ADDRESS, SIMILARITY_PORT
import json
import urllib2

_BASE_URL                     = 'http://%s:%i/similarity/'%(SIMILARITY_ADDRESS,SIMILARITY_PORT)
_URL_ADD_POINT                = 'add_point/'
_URL_DELETE_POINT             = 'delete_point/'
_URL_CONTAINS_POINT           = 'contains/'
_URL_NNSEARCH                 = 'nnsearch/'
_URL_NNRANGE                  = 'nnrange/'
_URL_API_SEARCH               = 'api_search/'
_URL_SOUNDS_DESCRIPTORS       = 'get_sounds_descriptors/'
_URL_SAVE                     = 'save/'


class SimilarityException(Exception):
    status_code = None

    def __init__(self, *args, **kwargs):
        super(SimilarityException, self).__init__(*args)
        self.status_code = kwargs['status_code']


def _get_url_as_json(url, data=None):
    if not data:
        f = urllib2.urlopen(url.replace(" ", "%20"))
    else:
        f = urllib2.urlopen(url.replace(" ", "%20"), data)
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
    def query(cls, target = None, filter = None, num_results = None, offset = None):
        if not target and not filter:
            raise Exception("At least descriptors_target or descriptors_filter should be specified")
        url = _BASE_URL + _URL_NNRANGE + '?'
        if target:
            url += '&target=' + str(target)
        if filter:
            url += '&filter=' + str(filter)
        if num_results:
            url += '&num_results=' + str(num_results)
        if offset:
            url += '&offset=' + str(offset)

        j = _get_url_as_json(url)
        r = _result_or_exception(j)

        return r

    @classmethod
    def api_search(cls, target_type=None, target=None, filter=None, preset=None, metric_descriptor_names=None, num_results=None, offset=None, file=None):
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

        j = _get_url_as_json(url, data=file)
        r = _result_or_exception(j)

        return r

    @classmethod
    def add(cls, sound_id, yaml_path):
        url = _BASE_URL + _URL_ADD_POINT + '?' + 'sound_id=' + str(sound_id)  + '&location=' + str(yaml_path)
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
