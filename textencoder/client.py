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

import json
import urllib.request

from django.conf import settings
from django.core.cache import cache

_BASE_URL = "http://%s:%i/" % (settings.TEXTENCODER_ADDRESS, settings.TEXTENCODER_PORT)
_URL_ENCODE_TEXT = "encode_text/"


def _get_url_as_json(url):
    f = urllib.request.urlopen(url.replace(" ", "%20"), timeout=settings.TEXTENCODER_TIMEOUT)  # noqa: S310
    resp = f.read()
    return json.loads(resp)


def _result_or_exception(result):
    if not result["error"]:
        return result["result"]
    else:
        raise Exception(result["result"])


class TextEncoder(object):
    @classmethod
    def encode_text(cls, input_text, model):
        cache_key = f"text-encoding-{model}-{input_text}"
        result = cache.get(cache_key, None)
        if result is None:
            url = (
                _BASE_URL
                + _URL_ENCODE_TEXT
                + "?"
                + "input="
                + urllib.parse.quote(input_text)
                + "&model="
                + urllib.parse.quote(model)
            )
            result = _result_or_exception(_get_url_as_json(url))
            cache.set(cache_key, result, settings.TEXTENCODER_CACHE_TIME)

        return result
