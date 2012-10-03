from similarity.similarity_settings import SIMILARITY_ADDRESS, SIMILARITY_PORT
import json
import urllib2

_BASE_URL                     = 'http://%s:%i/similarity/'%(SIMILARITY_ADDRESS,SIMILARITY_PORT)
_URL_ADD_POINT                = 'add_point/'
_URL_DELETE_POINT             = 'delete_point/'
_URL_CONTAINS_POINT           = 'contains_point/'
_URL_NNSEARCH                 = 'nnsearch/'
_URL_NNRANGE                  = 'nnrange/'
_URL_SAVE                     = 'save/'


def _get_url_as_json(url):
    f = urllib2.urlopen(url)
    resp = f.read()
    return json.loads(resp)


class Similarity():

    @classmethod
    def search(cls, sound_id, num_results, preset = False):
        url = _BASE_URL + _URL_NNSEARCH + '?' + 'sound_id=' + str(sound_id) + '&num_results=' + str(num_results) + '&preset=' + preset
        result = _get_url_as_json(url)
        return result['result']


'''
    @classmethod
    def query(cls, query_parameters, num_results):
        params = {'type': 'Query',
                  'query_parameters': query_parameters,
                  'num_results': num_results}
        return messenger.call_service(REQREP_ADDRESS, params)

    @classmethod
    def add(cls, sound_id, yaml):
        params = {'type': 'AddSound',
                  'sound_id': sound_id,
                  'yaml': yaml}
        return messenger.call_service(REQREP_ADDRESS, params)


    @classmethod
    def delete(cls, sound_id):
        params = {'type': 'DeleteSound',
                  'sound_id': sound_id}
        return messenger.call_service(REQREP_ADDRESS, params)


    @classmethod
    def contains(cls, sound_id):
        params = {'type': 'Contains',
                  'sound_id': sound_id}
        return messenger.call_service(REQREP_ADDRESS, params)
'''

