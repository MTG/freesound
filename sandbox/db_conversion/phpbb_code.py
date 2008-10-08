import re

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
    tmp = re.compile(r"\[(/?)font[^\]]*\]", re.IGNORECASE).sub(u"", text)
    tmp = re.compile(r"\[(/?)size[^\]]*\]", re.IGNORECASE).sub(u"", tmp)
    return re.compile(r"\[(/?)color[^\]]*\]", re.IGNORECASE).sub(u"", tmp)

def render_to_html(bbcode):
    return render_destroy(render_ul(render_bius(render_url(render_image(render_quote(bbcode))))))


def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()