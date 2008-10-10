import unittest, re
from BeautifulSoup import BeautifulSoup, Comment

def smart_character_decoding(string):
    try:
        decoded = string.decode("utf-8")
        if any(ord(c) >= 128 for c in string):
            print "utf-8", decoded.encode('utf-8')
        return decoded
    except UnicodeError:
        decoded = string.decode("latin-1")
        return decoded

def shout_percentage(string):
    if len(string):
        return sum(1 for s in string if s != s.lower() or s == u"!") / float(len(string))
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
    return shout_percentage(string) > 0.6


# returns if the string ends with any of the endinggs
def ends_with_any(string, endings):
    return any(string.endswith(end) for end in endings)

# returns if the string starts with any of the starts
def starts_with_any(string, starts):
    return any(string.startswith(end) for end in endings)


url_regex = re.compile(r"(http:\/\/[\w_-]+\.[\.\w_-]+\/?[@\.\w/_\?=~;:%#&\+-]*)", re.IGNORECASE)

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
    u'<ul><p>123hello<strong>there http://www</strong></p></ul>'
    >>> clean_html(u'abc http://www.google.com abc')
    u'abc <a href="http://www.google.com" rel="nofollow">http://www.google.com</a> abc'
    >>> clean_html(u'GALORE: http://freesound.iua.upf.edu/samplesViewSingle.php?id=22092\\nFreesound Moderator')
    u'GALORE: <a href="http://freesound.iua.upf.edu/samplesViewSingle.php?id=22092" rel="nofollow">http://freesound.iua.upf.edu/samplesViewSingle.php?id=22092</a>\\nFreesound Moderator'
    """
    
    delete_tags = [u"script", u"style", u"head"]
    ok_tags = [u"a", u"img", u"strong", u"b", u"em", u"i", u"u", u"p", u"br", u"ul", u"li"]
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
                    if u"href" not in dict(element.attrs) or not url_regex.match(element[u"href"]):
                        replace_element_by_children(soup, element)
                    else:
                        element["rel"] = u"nofollow"
                elif element.name == u"img":
                    if u"src" not in dict(element.attrs) or not url_regex.match(element[u"src"]):
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


def render_ul(text):
    """
    >>> render_ul(u"[list:123][*:12345]google[/list:1234]")
    u'<ul><li>google</ul>'
    >>> render_ul(u"[list:123][*:12345]google\\n[*:12345]google\\n[*:12345]google[/list:1234]")
    u'<ul><li>google\\n<li>google\\n<li>google</ul>'
    >>> render_ul(u"[LIST:123][*:12345]google[/LIST:1234]")
    u'<ul><li>google</ul>'
    """
    def repl(match):
        closing, = match.groups()
        if closing:
            return u"</ul>"
        else:
            return u"<ul>"

    tmp = re.compile(r"\[(/?)list[^\]]*\]", re.IGNORECASE).sub(repl, text)
    
    return re.compile(r"\[\*[^\]]*\]", re.IGNORECASE).sub(r"<li>", tmp)


def render_bius(text):
    """
    >>> render_bius(u"[b]google[/b]")
    u'<strong>google</strong>'
    >>> render_bius(u"[b:123]google[/b:1234]")
    u'<strong>google</strong>'
    >>> render_bius(u"[i:123]google[/i:1234]")
    u'<em>google</em>'
    >>> render_bius(u"[u:123]google[/u:1234]")
    u'<u>google</u>'
    >>> render_bius(u"[s:123]google[/s:1234]")
    u'<strike>google</strike>'
    """
    def repl(match):
        closing, type, = match.groups()
        
        tmp = u"<"
        if closing:
            tmp += u"/"
         
        if type.lower() == u"b":
            return tmp + u"strong>"
        if type.lower() == "i":
            return tmp + u"em>"
        if type.lower() == "u":
            return tmp + u"u>"
        if type.lower() == "s":
            return tmp + u"strike>"
        
    return re.compile(r"\[(/?)(b|i|u|s)[^\]]*\]", re.IGNORECASE).sub(repl, text)


def render_url(text):
    """
    >>> render_url(u"[url=http://www.google.com]google[/url]")
    u'<a href="http://www.google.com">google</a>'
    >>> render_url(u"[url=http://www.google.com][/url]")
    u'<a href="http://www.google.com">http://www.google.com</a>'
    >>> render_url(u"[url=]http://www.google.com[/url]")
    u'<a href="http://www.google.com">http://www.google.com</a>'
    >>> render_url(u"[url]http://www.google.com[/url]")
    u'<a href="http://www.google.com">http://www.google.com</a>'
    >>> render_url(u"[url]http://www.google.com[/url] hello [url]http://www.google.com[/url]")
    u'<a href="http://www.google.com">http://www.google.com</a> hello <a href="http://www.google.com">http://www.google.com</a>'
    """
    def repl(match):
        (url, text) = match.groups()
        if url == None or url == "":
            return u"<a href=\"%s\">%s</a>" % (text,text)
        if text == None or text == "":
            return u"<a href=\"%s\">%s</a>" % (url,url)
        else:
            return u"<a href=\"%s\">%s</a>" % (url,text)
        
    return re.compile(r"\[url=?([^\]]+)?\]([^\]]*)\[/url\]", re.IGNORECASE).sub(repl, text)


def render_image(text):
    """
    >>> render_image(u"[img:2345]http://www.google.com/img.png[/img]")
    u'<img src="http://www.google.com/img.png" />'
    """
    return re.compile(r"\[img[^\]]*\]([^\]]*)\[/img\]", re.IGNORECASE).sub(r'<img src="\1" />', text)


def render_quote(text):
    """
    >>> render_quote("[quote:c28ff2d572=\\"bram\\"]hello[/quote:234rtfgv]")
    u'<blockquote><em>bram</em>\\nhello</blockquote>'
    >>> render_quote("[quote:c28ff2d572]hello[/quote:234rtfgv]")
    u'<blockquote>hello</blockquote>'
    """
    tmp = re.compile(r"\[quote[^\=]*=\"([^\"]+)\"\]", re.IGNORECASE).sub(r'<blockquote><em>\1</em>\n', text)
    tmp = re.compile(r"\[quote[^\]]*\]", re.IGNORECASE).sub(r'<blockquote>', tmp)
    return unicode(re.compile(r"\[/quote[^\]]*\]", re.IGNORECASE).sub(r'</blockquote>', tmp))


def render_destroy(text):
    return re.compile(r"\[(/?)(email|font|size|color|code)[^\]]*\]", re.IGNORECASE).sub(u"", text)

def render_bbcode_to_html(bbcode):
    return clean_html()

def prepare_for_insert(text, bb_code=True, html_code=True, verbose=False):
    
    # unescape all bouble backslashes, quotes and ampersands
    # these are stored escaped in mysql...
    output = re.sub(r"\\+", r"\\", text).replace(u"\\\"", u"\"").replace(u"\\\'", u"\'")
    
    if bb_code:
        output = render_destroy(render_ul(render_bius(render_url(render_image(render_quote(output))))))
        
    if html_code:
        output = clean_html(output)
    
    output = output.replace(u"\\", u"\\\\").replace(u"\t", u"\\t").replace(u"\n", u"\\n").replace(u"\r", u"\\r")
    
    if verbose:
            matches = re.findall(r"\[[^\[]*\]", output)
            if matches:
                print "-------------------------------"
                print list(map(lambda string: string.encode("ascii", "ignore"), matches))
                
    return output

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()