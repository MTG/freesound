import json
import urllib2
from urllib2 import quote

TAGRECOMMENDATION_ADDRESS = 'fs-labs.s.upf.edu'
TAGRECOMMENDATION_PORT = 8010

_BASE_URL                      = 'http://%s:%i/tagrecommendation/' % (TAGRECOMMENDATION_ADDRESS, TAGRECOMMENDATION_PORT)
_URL_RECOMMEND_TAGS_CATEGORY   = 'recommend_tags_per_category/'
_URL_RECOMMEND_TAGS            = 'recommend_tags/'
_URL_RECOMMEND_TAG_CATEGORIES  = 'recommend_categories/'
_URL_ALL_TAG_CATEGORIES        = 'all_tag_categories/'
_URL_ADD_SOUND_TO_INDEX        = 'add_sound_to_index/'
_URL_SAVE_INDEX                = 'save_index/'
_URL_UPDATE_MATRICES           = 'update_matrices/'
_URL_POPULATE_ONTOLOGY         = 'populate_individuals_ontology/'
_URL_SAVE_ONTOLOGY             = 'save_individuals_ontology/'


def my_quote(string):
    # quote strings, but allow ','
    return quote(str(string)).replace('%2C', ',')

def _get_url_as_json(url):
    f = urllib2.urlopen(url.replace(" ", "%20"))
    resp = f.read()
    return json.loads(resp)


def _result_or_exception(result):
    if not result['error']:
        return result['result']
    else:
        raise Exception(result['result'])


class NewTagRecommendation():

    @classmethod
    def recommend_tags_category(cls, input_tags, category, max_number_of_tags=None):
        url = _BASE_URL + _URL_RECOMMEND_TAGS_CATEGORY + '?input_tags=' + my_quote(input_tags) + '&category=' + my_quote(category)
        if max_number_of_tags:
            url += '&max_number_of_tags=' + str(max_number_of_tags)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def recommend_tags(cls, input_tags, max_number_of_tags=None):
        url = _BASE_URL + _URL_RECOMMEND_TAGS + '?input_tags=' + my_quote(input_tags)
        if max_number_of_tags:
            url += '&max_number_of_tags=' + str(max_number_of_tags)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def recommend_categories(cls, input_tags):
        url = _BASE_URL + _URL_RECOMMEND_TAG_CATEGORIES + '?input_tags=' + my_quote(input_tags)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def all_tag_categories(cls):
        url = _BASE_URL + _URL_ALL_TAG_CATEGORIES
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def add_sound_to_index(cls, sound_id, input_tags):
        url = _BASE_URL + _URL_ADD_SOUND_TO_INDEX + '?sound_id=' + str(sound_id) + '&sound_tags=' + my_quote(input_tags)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def save_index(cls):
        url = _BASE_URL + _URL_SAVE_INDEX
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def update_matrices(cls):
        url = _BASE_URL + _URL_UPDATE_MATRICES
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def populate_ontology(cls, tag, tag_class):
        url = _BASE_URL + _URL_POPULATE_ONTOLOGY + '?tag=' + my_quote(tag) + '&tag_class=' + my_quote(tag_class)
        return _result_or_exception(_get_url_as_json(url))

    @classmethod
    def save_ontology(cls):
        url = _BASE_URL + _URL_SAVE_ONTOLOGY
        return _result_or_exception(_get_url_as_json(url))