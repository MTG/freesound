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
import unicodedata
import bleach
from html5lib.filters.base import Filter
from functools import partial
from htmlentitydefs import name2codepoint
from django.utils.encoding import smart_unicode
from sounds.templatetags.sound_signature import SOUND_SIGNATURE_SOUND_ID_PLACEHOLDER, \
    SOUND_SIGNATURE_SOUND_URL_PLACEHOLDER


def slugify(s, entities=True, decimal=True, hexadecimal=True, instance=None, slug_field='slug', filter_dict=None):
    """ slugify with character translation which translates foreign characters to regular ascii equivalents """
    s = smart_unicode(s)

    #  character entity reference
    if entities:
        s = re.sub('&(%s);' % '|'.join(name2codepoint), lambda m: unichr(name2codepoint[m.group(1)]), s)

    #  decimal character reference
    if decimal:
        try:
            s = re.sub('&#(\d+);', lambda m: unichr(int(m.group(1))), s)
        except:
            pass

    #  hexadecimal character reference
    if hexadecimal:
        try:
            s = re.sub('&#x([\da-fA-F]+);', lambda m: unichr(int(m.group(1), 16)), s)
        except:
            pass

    #  translate
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')

    #  replace unwanted characters
    s = re.sub(r'[^-a-z0-9]+', '-', s.lower())

    #  remove redundant -
    s = re.sub('-{2,}', '-', s).strip('-')

    slug = s

    if instance:
        def get_query():
            query = instance.__class__.objects.filter(**{slug_field: slug})
            if filter_dict:
                query = query.filter(**filter_dict)
            if instance.pk:
                query = query.exclude(pk=instance.pk)
            return query
        counter = 1
        while get_query():
            slug = "%s-%s" % (s, counter)
            counter += 1

    return slug.lower()


def shout_percentage(string):
    if len(string):
        return sum(1 for s in string if s != s.lower() or s == "!") / float(len(string))
    else:
        return 0


def is_shouting(string):
    """
    >>> is_shouting('')
    False
    >>> is_shouting('HELLO THIS IS SHOUTING!!!')
    True
    >>> is_shouting('This is a phrase WITH SONE emphasis!!')
    False
    >>> is_shouting('This is a regular phrase.')
    False
    """
    if len(string) < 5:
        return False
    return shout_percentage(string) > 0.6


# returns if the string ends with any of the endinggs
def endswithone(string, endings):
    reduce(lambda a,b: a or string.endswith(b), endings, False)


# returns if the string starts with any of the starts
def startswithone(string, starts):
    reduce(lambda a,b: a or string.startswith(b), starts, False)


url_regex = re.compile("(https?://\S+)", re.IGNORECASE)


def replace_element_by_children(soup, element):
    """
    replace an element in the DOM with it's child nodes
    """
    parent = element.parent

    if not parent:
        parent = soup

    # afterwards we need to insert the children where the parent used to be!
    position_in_parent = 0
    for c in parent.contents:
        if c == element:
            break
        else:
            position_in_parent += 1

    # in reverse order, insert the child elements in their place.
    for el in element.contents[::-1]:
        parent.insert(position_in_parent, el)

    # delete the element
    element.extract()


def nofollow(attrs, new=False):
    attrs[(None, u'rel')] = u'nofollow'
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

def clean_html(input):
    # Reaplce html tags from user input, see utils.test for examples

    ok_tags = [u"a", u"img", u"strong", u"b", u"em", u"i", u"u", u"ul", u"li", u"p", u"br",  u"blockquote", u"code"]
    ok_attributes = {u"a": [u"href", u"rel"], u"img": [u"src", u"alt", u"title"]}
    # all other tags: replace with the content of the tag

    # If input contains link in the format: <http://> then convert it to < http:// >
    # This is because otherwise the library recognizes it as a tag and breaks the link.
    input = re.sub("\<(http\S+?)\>", r'< \1 >', input)

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
    return ''.join(c for c in text if (ord(c) >= 32 or ord(c) in [9,10,13]))


def text_may_be_spam(text):
    """
    >>> text_may_be_spam(u'')
    False
    >>> text_may_be_spam(u'  ')
    False
    >>> text_may_be_spam(u'this is the content of a blog post')
    False
    >>> text_may_be_spam(u'this post contains an http:// link')
    True
    >>> text_may_be_spam(u'this post contains an https:// link')
    True
    >>> text_may_be_spam(u'this post contains non-basic ascii characters :')
    True
    >>> text_may_be_spam(u'this post contains non-basic ascii characters \xc3')
    True
    >>> text_may_be_spam(u'this post contains few numbers 1245')
    False
    >>> text_may_be_spam(u'this post contains more numbers 1234567')
    True
    >>> text_may_be_spam(u'this post contains even more numbers 123456789')
    True
    >>> text_may_be_spam(u'this post contains an@email.com')
    True
    >>> text_may_be_spam(u'this post contains short.url')
    True
    >>> text_may_be_spam(u'BLaCk MaGiC SpEcIaLiSt babaji')
    True
    >>> text_may_be_spam(u'love marriage problem solution')
    True
    >>> text_may_be_spam(u'fbdad8fbdad8fbdad8')
    True
    >>> text_may_be_spam(u'fbdad8')
    True
    """

    # If empty text
    if text.strip() == '':
        return False

    # If link in text
    if "http://" in text or "https://" in text:
        return True

    # If emails or short urls
    if re.search("[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,3}(\s|$|\/|\]|\.)",  text):
        return True

    # If consecutive numbers
    if re.search("\(|\)|\d{7}",  text):
        return True

    # If non ascii characters
    if len(re.sub("[^A-Za-z0-9 ]", "", text, flags=re.UNICODE)) < len(text):
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


def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
