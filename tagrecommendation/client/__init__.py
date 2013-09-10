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

from tagrecommendation.tagrecommendation_settings import TAGRECOMMENDATION_ADDRESS, TAGRECOMMENDATION_PORT
import json
import urllib2

_BASE_URL                     = 'http://%s:%i/tagrecommendation/' % (TAGRECOMMENDATION_ADDRESS, TAGRECOMMENDATION_PORT)
_URL_RECOMMEND_TAGS           = 'recommend_tags/'


def _get_url_as_json(url):
    f = urllib2.urlopen(url.replace(" ","%20"))
    resp = f.read()
    return json.loads(resp)


def _result_or_exception(result):
    if not result['error']:
        return result['result']
    else:
        raise Exception(result['result'])


class TagRecommendation():

    @classmethod
    def recommend_tags(cls, input_tags, max_number_of_tags=None):
        url = _BASE_URL + _URL_RECOMMEND_TAGS + '?' + 'input_tags=' + ",".join(input_tags)
        if max_number_of_tags:
            url += '&max_number_of_tags=' + str(max_number_of_tags)
        return _result_or_exception(_get_url_as_json(url))
