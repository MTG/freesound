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

import re
from functools import partial

import bleach
from bleach.html5lib_shim import Filter

from sounds.templatetags.sound_signature import SOUND_SIGNATURE_SOUND_ID_PLACEHOLDER, \
    SOUND_SIGNATURE_SOUND_URL_PLACEHOLDER


def shout_percentage(string):
    if len(string):
        return sum(1 for s in string if s != s.lower() or s == "!") / float(len(string))
    else:
        return 0


def is_shouting(string):
    """Test if a string sounds like shouting (more than 60% uppercase)"""
    if len(string) < 5:
        return False
    return shout_percentage(string) > 0.6


url_regex = re.compile(r"(https?://\S+)", re.IGNORECASE)


def nofollow(attrs, new=False):
    attrs[(None, 'rel')] = 'nofollow'
    return attrs


def is_valid_url(url):
    url_exceptions = [SOUND_SIGNATURE_SOUND_ID_PLACEHOLDER, SOUND_SIGNATURE_SOUND_URL_PLACEHOLDER]
    return url_regex.match(url) or url in url_exceptions


class EmptyLinkFilter(Filter):
    def __iter__(self):
        remove_end_tag = False
        for token in Filter.__iter__(self):
            # only check anchor tags
            if 'name' in token and token['name'] == 'a' and token['type'] in ['StartTag', 'EndTag']:
                if token['type'] == 'StartTag':
                    remove_end_tag = True
                    for attr, value in token['data'].items():
                        if attr == (None, 'href') and value != '' and is_valid_url(value):
                            remove_end_tag = False
                    if remove_end_tag:
                        continue
                elif token['type'] == 'EndTag' and remove_end_tag:
                    remove_end_tag = False
                    continue
            yield token


def clean_html(input, ok_tags=[], ok_attributes={}):
    # Replace html tags from user input, see utils.test for examples

    # ok_tags and ok_attributes are used to specify which tags and attributes are allowed
    # They should look like this:
    #  ok_tags = ["a", "img", "strong", "b", "em", "i", "u", "ul", "li", "p", "br",  "blockquote", "code"]
    #  ok_attributes = {"a": ["href", "rel"], "img": ["src", "alt", "title"]}
    # all other tags: replace with the content of the tag

    # If input contains link in the format: <http://> then convert it to < http:// >
    # This is because otherwise the library recognizes it as a tag and breaks the link.
    input = re.sub(r"\<(http\S+?)\>", r'< \1 >', input)

    cleaner = bleach.Cleaner(
            filters=[
                EmptyLinkFilter,
                partial(bleach.linkifier.LinkifyFilter, callbacks=[nofollow]),
                ],
            attributes=ok_attributes,
            tags=ok_tags,
            strip=True)
    output = cleaner.clean(input)
    return output


def remove_control_chars(text):
    return ''.join(c for c in text if (ord(c) >= 32 or ord(c) in [9, 10, 13]))


def text_has_hyperlink(text):
    return "http://" in text or "https://" in text


def text_may_be_spam(text):
    """Some heuristics to determine if some text may be spam.
    Arguments:
        text (basestring): the string to check
    Returns (bool): True if the text may be spam, False otherwise
    """

    # If empty text
    if text.strip() == '':
        return False

    # If link in text
    if text_has_hyperlink(text):
        return True

    # If emails or short urls
    if re.search(r"[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,3}(\s|$|\/|\]|\.)",  text):
        return True

    # If consecutive numbers
    if re.search(r"\(|\)|\d{7}",  text):
        return True

    # If non ascii characters
    if len(re.sub(r"[^A-Za-z0-9 ]", "", text, flags=re.UNICODE)) < len(text):
        return True

    # Love, marriage and other everyday topics ;)
    if any([element in text.lower() for element in ['love', 'marriage', 'black magic']]):
        return True

    # Suspicious text
    if len(text.split()) == 1:
        return True
    if len(set(list(text))) < 10:
        return True

    return False
