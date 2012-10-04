from similarity.similarity_settings import SIMILARITY_ADDRESS, SIMILARITY_PORT
import json
import urllib2

_BASE_URL                     = 'http://%s:%i/similarity/'%(SIMILARITY_ADDRESS,SIMILARITY_PORT)
_URL_ADD_POINT                = 'add_point/'
_URL_DELETE_POINT             = 'delete_point/'
_URL_CONTAINS_POINT           = 'contains/'
_URL_NNSEARCH                 = 'nnsearch/'
_URL_NNRANGE                  = 'nnrange/'
_URL_SAVE                     = 'save/'


def _get_url_as_json(url):
    f = urllib2.urlopen(url)
    resp = f.read()
    return json.loads(resp)

def _result_or_exception(result):
    if not result['error']:
        return result['result']
    else:
        raise Exception(result['result'])

class Similarity():

    @classmethod
    def search(cls, sound_id, num_results = None, preset = None):
        url = _BASE_URL + _URL_NNSEARCH + '?' + 'sound_id=' + str(sound_id)
        if num_results:
              url += '&num_results=' + str(num_results)
        if preset:
              url += '&preset=' + preset
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def query(cls, target = None, filter = None, num_results = None):
        if not target and not filter:
            raise Exception("At least a target or a filter should be specified")
        url = _BASE_URL + _URL_NNRANGE + '?'
        if target:
            url += '&t=' + str(target)
        if filter:
            url += '&f=' + str(filter)
        if num_results:
            url += '&num_results=' + str(num_results)
        return _result_or_exception(_get_url_as_json(url))

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
