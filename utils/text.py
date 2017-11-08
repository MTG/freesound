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
from BeautifulSoup import BeautifulSoup, Comment
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


def clean_html(input):
    """
    >>> clean_html(u'a b c d')
    u'a b c d'
    >>> clean_html(u'<a href="http://www.google.com" rel="squeek">google</a>')
    u'<a href="http://www.google.com" rel="nofollow">google</a>'
    >>> clean_html(u'<a href="http://www.google.com">google</a>')
    u'<a href="http://www.google.com" rel="nofollow">google</a>'
    >>> clean_html(u'<h1>this should return the <strong>substring</strong> just <b>fine</b></h1>')
    u'this should return the <strong>substring</strong> just <b>fine</b>'
    >>> clean_html(u'<table><tr><td>amazing</td><td>grace</td></tr></table>')
    u'amazinggrace'
    >>> clean_html(u'<a href="javascript:void(0)">click me</a>')
    u'click me'
    >>> clean_html(u'<p class="hello">click me</p>')
    u'<p>click me</p>'
    >>> clean_html(u'<a></a>')
    u''
    >>> clean_html(u'<p>         </p>')
    u'<p> </p>'
    >>> clean_html(u'<a>hello</a>')
    u'hello'
    >>> clean_html(u'<p class="hello" id="1">a<br/>b<br/></a>')
    u'<p>a<br />b<br /></p>'
    >>> clean_html(u'<p></p>')
    u'<p></p>'
    >>> clean_html(u'<A REL="nofollow" hREF="http://www.google.com"><strong>http://www.google.com</strong></a>')
    u'<a href="http://www.google.com" rel="nofollow"><strong>http://www.google.com</strong></a>'
    >>> clean_html(u'<a rel="nofollow" href="http://www.google.com"><strong>http://www.google.com</strong></a>')
    u'<a href="http://www.google.com" rel="nofollow"><strong>http://www.google.com</strong></a>'
    >>> clean_html(u'http://www.google.com <a href="">http://www.google.com</a>')
    u'<a href="http://www.google.com" rel="nofollow">http://www.google.com</a> <a href="http://www.google.com" rel="nofollow">http://www.google.com</a>'
    >>> clean_html(u'<ul><p id=5><a href="123">123</a>hello<tr></tr><strong class=156>there http://www</strong></p></ul>')
    u'<p>123hello<strong>there <a href="http://www" rel="nofollow">http://www</a></strong></p>'
    >>> clean_html(u'abc http://www.google.com abc')
    u'abc <a href="http://www.google.com" rel="nofollow">http://www.google.com</a> abc'
    >>> clean_html(u'GALORE: https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092\\nFreesound Moderator')
    u'GALORE: <a href="https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092" rel="nofollow">https://freesound.iua.upf.edu/samplesViewSingle.php?id=22092</a>\\nFreesound Moderator'
    >>> clean_html(u'<a href="${sound_id}">my sound id</a>')
    u'<a href="${sound_id}" rel="nofollow">my sound id</a>'
    >>> clean_html(u'<a href="${sound_url}">my sound url</a>')
    u'<a href="${sound_url}" rel="nofollow">my sound url</a>'
    """

    def is_valid_url(url):
        url_exceptions = [SOUND_SIGNATURE_SOUND_ID_PLACEHOLDER, SOUND_SIGNATURE_SOUND_URL_PLACEHOLDER]
        return url_regex.match(url) or url in url_exceptions
    
    delete_tags = [u"script", u"style", u"head"]
    ok_tags = [u"a", u"img", u"strong", u"b", u"em", u"i", u"u", u"p", u"br",  u"blockquote", u"code"]
    ok_attributes = {u"a": [u"href"], u"img": [u"src", u"alt", u"title"]}
    # all other tags: replace with the content of the tag
    
    soup = BeautifulSoup(input, fromEncoding="utf-8")
    
    # delete all comments
    [comment.extract() for comment in soup.findAll(text=lambda text:isinstance(text, Comment))]

    for element in soup.findAll():
        if element.name in delete_tags:
            element.extract()
            continue
        
        if element.name not in ok_tags:
            replace_element_by_children(soup, element)
            continue
            
        try:
            if element.name in ok_attributes.keys():
                # delete all attributes we don't want
                for (attr_name, attr_value) in element.attrs:
                    if attr_name not in ok_attributes[element.name]:
                        del element[attr_name]

                if element.name == "a":
                    if u"href" not in dict(element.attrs) or not is_valid_url(element[u"href"]):
                        replace_element_by_children(soup, element)
                    else:
                        element["rel"] = u"nofollow"
                elif element.name == u"img":
                    if u"src" not in dict(element.attrs) or not is_valid_url(element[u"src"]):
                        replace_element_by_children(soup, element)
            else:
                # these should not have any attributes
                element.attrs = []
        except AttributeError:
            if element.name in ok_attributes.keys():
                replace_element_by_children(soup, element)

    for text in soup.findAll(text=url_regex):
        if not text.findParents(u'a'):
            text.replaceWith(url_regex.sub(r'<a href="\1" rel="nofollow">\1</a>', text))
    
    return unicode(soup)


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
