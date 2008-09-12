# -*- coding: UTF-8 -*-

"""
Post Markup
Author: Will McGugan (http://www.willmcgugan.com)
"""

__version__ = "1.1.0"

import re
from urllib import quote, unquote, quote_plus
from urlparse import urlparse, urlunparse

pygments_available = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, ClassNotFound
    from pygments.formatters import HtmlFormatter
except ImportError:
    # Make Pygments optional
    pygments_available = False



def annotate_link(domain):
    """This function is called by the url tag. Override to disable or change behaviour.
    
    domain -- Domain parsed from url
    
    """
    return u" [%s]"%domain


re_url = re.compile(r"((https?):((//)|(\\\\))+[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.MULTILINE| re.UNICODE)


re_html=re.compile('<.*?>|\&.*?\;')
def textilize(s):
    """Remove markup from html"""
    return re_html.sub("", s)

re_excerpt = re.compile(r'\[".*?\]+?.*?\[/".*?\]+?', re.DOTALL)
re_remove_markup = re.compile(r'\[.*?\]', re.DOTALL)

def remove_markup(post):
    """Removes html tags from a string."""
    return re_remove_markup.sub("", post)

def get_excerpt(post):
    """Returns an excerpt between ["] and [/"]

    post -- BBCode string"""

    match = re_excerpt.search(post)
    if match is None:
        return ""
    excerpt = match.group(0)
    excerpt = excerpt.replace(u'\n', u"<br/>")
    return remove_markup(excerpt)

def strip_bbcode(bbcode):
    
    """ Strips bbcode tags from a string.
    
    bbcode -- A string to remove tags from
    
    """    
    
    return u"".join([t[1] for t in PostMarkup.tokenize(bbcode) if t[0] == PostMarkup.TOKEN_TEXT])        


def create(include=None, exclude=None, use_pygments=True, **kwargs):
    
    """Create a postmarkup object that converts bbcode to XML snippets.

    include -- List or similar iterable containing the names of the tags to use
               If omitted, all tags will be used
    exclude -- List or similar iterable containing the names of the tags to exclude.
               If omitted, no tags will be excluded
    use_pygments -- If True, Pygments (http://pygments.org/) will be used for the code tag,
                    otherwise it will use <pre>code</pre>
    """
    
    postmarkup = PostMarkup()
    postmarkup_add_tag = postmarkup.tag_factory.add_tag
    
    def add_tag(tag_class, name, *args, **kwargs):
        if include is None or name in include:
            if exclude is not None and name in exclude:
                return
            postmarkup_add_tag(tag_class, name, *args, **kwargs)


    
    add_tag(SimpleTag, 'b', 'strong')
    add_tag(SimpleTag, 'i', 'em')
    add_tag(SimpleTag, 'u', 'u')
    add_tag(SimpleTag, 's', 'strike')
        
    add_tag(LinkTag, 'link', **kwargs)
    add_tag(LinkTag, 'url', **kwargs)
    
    add_tag(QuoteTag, 'quote')
    
    add_tag(SearchTag, u'wiki',
            u"http://en.wikipedia.org/wiki/Special:Search?search=%s", u'wikipedia.com', **kwargs)
    add_tag(SearchTag, u'google',
            u"http://www.google.com/search?hl=en&q=%s&btnG=Google+Search", u'google.com', **kwargs)
    add_tag(SearchTag, u'dictionary',
            u"http://dictionary.reference.com/browse/%s", u'dictionary.com', **kwargs)
    add_tag(SearchTag, u'dict',
            u"http://dictionary.reference.com/browse/%s", u'dictionary.com', **kwargs)
    
    add_tag(ImgTag, u'img')
    add_tag(ListTag, u'list')
    add_tag(ListItemTag, u'*')
    
    add_tag(SizeTag, u"size")
    add_tag(ColorTag, u"color")
    add_tag(CenterTag, u"center")
    
    if use_pygments:
        assert pygments_available, "Install Pygments (http://pygments.org/) or call create with use_pygments=False"
        add_tag(PygmentsCodeTag, u'code', **kwargs)
    else:
        add_tag(CodeTag, u'code', **kwargs)

    return postmarkup



_postmarkup = None
def render_bbcode(bbcode, encoding="ascii", exclude_tags=None, auto_urls=True):

    """Renders a bbcode string in to XHTML. This is a shortcut if you don't
    need to customize any tags.

    bbcode -- A string containing the bbcode
    encoding -- If bbcode is not unicode, then then it will be encoded with
    this encoding (defaults to 'ascii'). Ignore the encoding if you already have
    a unicode string

    """
    
    global _postmarkup
    if _postmarkup is None:
        _postmarkup = create(use_pygments=pygments_available, pygments_line_numbers=True)    
        
    return _postmarkup(bbcode, encoding, exclude_tags=exclude_tags, auto_urls=auto_urls)


class TagBase(object):
    
    def __init__(self, name, enclosed=False, auto_close=False, inline=False, strip_first_newline=False, **kwargs):
        """Base class for all tags.
        
        name -- The name of the bbcode tag
        enclosed -- True if the contents of the tag should not be bbcode processed.
        auto_close -- True if the tag is standalone and does not require a close tag.
        inline -- True if the tag generates an inline html tag.
        
        """
        
        self.name = name
        self.enclosed = enclosed
        self.auto_close = auto_close
        self.inline = inline
        self.strip_first_newline = strip_first_newline
        
        self.open_pos = None
        self.close_pos = None
        self.open_node_index = None
        self.close_node_index = None
        
    def open(self, parser, params, open_pos, node_index):
        """ Called when the open tag is initially encountered. """
        self.params = params
        self.open_pos = open_pos
        self.open_node_index = node_index        
    
    def close(self, parser, close_pos, node_index):
        """ Called when the close tag is initially encountered. """
        self.close_pos = close_pos
        self.close_node_index = node_index
        
    def render_open(self, parser, node_index):
        """ Called to render the open tag. """
        pass
    
    def render_close(self, parser, node_index):
        """ Called to render the close tag. """
        pass
                
    def get_contents(self, parser):
        """Returns the string between the open and close tag.""" 
        return parser.markup[self.open_pos:self.close_pos]
    
    def get_contents_text(self, parser):
        """Returns the string between the the open and close tag, minus bbcode tags."""        
        return u"".join( parser.get_text_nodes(self.open_node_index, self.close_node_index) )
    
    def skip_contents(self, parser):
        """Skips the contents of a tag while rendering."""
        parser.skip_to_node(self.close_node_index)
        
    def __str__(self):
        return '[%s]'%self.name


class SimpleTag(TagBase):
    
    """A tag that can be rendered with a simple substitution. """
    
    def __init__(self, name, html_name, **kwargs):
        """ html_name -- the html tag to substitute."""
        TagBase.__init__(self, name, inline=True)
        self.html_name = html_name
            
    def render_open(self, parser, node_index):
        return u"<%s>"%self.html_name
    
    def render_close(self, parser, node_index):
        return u"</%s>"%self.html_name
    
    
class DivStyleTag(TagBase):
    
    """A simple tag that is replaces with a div and a style."""
    
    def __init__(self, name, style, value, **kwargs):
        TagBase.__init__(self, name)
        self.style = style
        self.value = value
        
    def render_open(self, parser, node_index):
        return u'<div style="%s:%s;">' % (self.style, self.value)
    
    def render_close(self, parser, node_index):
        return u'</div>'


class LinkTag(TagBase):
    
    def __init__(self, name, annotate_links=True, **kwargs):
        TagBase.__init__(self, name, inline=True)
        
        self.annotate_links = annotate_links
            

    def render_open(self, parser, node_index):  
              
        self.domain = u''
        tag_data = parser.tag_data
        nest_level = tag_data['link_nest_level'] = tag_data.setdefault('link_nest_level', 0) + 1
        
        if nest_level > 1:            
            return u""            
        
        if self.params:            
            url = self.params.strip()
        else:            
            url = self.get_contents_text(parser).strip()                   

        self.domain = ""
        #Unquote the url
        self.url = unquote(url)

        #Disallow javascript links
        if u"javascript:" in self.url.lower():
            return ""

        #Disallow non http: links
        url_parsed = urlparse(self.url)
        if url_parsed[0] and not url_parsed[0].lower().startswith(u'http'):
            return ""

        #Prepend http: if it is not present
        if not url_parsed[0]:
            self.url="http://"+self.url
            url_parsed = urlparse(self.url)

        #Get domain
        self.domain = url_parsed[1].lower()

        #Remove www for brevity
        if self.domain.startswith(u'www.'):
            self.domain = self.domain[4:]

        #Quote the url
        #self.url="http:"+urlunparse( map(quote, (u"",)+url_parsed[1:]) )
        #self.url = unicode( urlunparse([quote(component, safe='/=&?:+') for component in url_parsed]) )
        self.url = unicode( urlunparse([quote(component.encode("latin-1"), safe='/=&?:+') for component in url_parsed]) )
        print self.url
        
        if not self.url:
            return u""

        if self.domain:            
            return u'<a href="%s">'%self.url
        else:
            return u""
        
    def render_close(self, parser, node_index):        
        
        tag_data = parser.tag_data
        tag_data['link_nest_level'] -= 1
        
        if tag_data['link_nest_level'] > 0:
            return u''
                
        if self.domain:
            return u'</a>'+self.annotate_link(self.domain)
        else:
            return u''
        
    def annotate_link(self, domain=None):
        
        if domain and self.annotate_links:
            return annotate_link(domain)
        else:
            return u""
            

class QuoteTag(TagBase):
    
    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, strip_first_newline=True)
            
    def open(self, parser, *args):
        TagBase.open(self, parser, *args)        
    
    def close(self, parser, *args):
        TagBase.close(self, parser, *args)            
    
    def render_open(self, parser, node_index):        
        if self.params:
            return u'<blockquote><em>%s</em><br/>'%(PostMarkup.standard_replace(self.params))
        else:
            return u'<blockquote>'
            

    def render_close(self, parser, node_index):        
        return u"</blockquote>"
    
    
class SearchTag(TagBase):
    
    def __init__(self, name, url, label="", annotate_links=True, **kwargs):
        TagBase.__init__(self, name, inline=True)
        self.url = url
        self.label = label
        self.annotate_links = annotate_links
        
    def render_open(self, parser, node_idex):
        
        if self.params:
            search=self.params
        else:
            search=self.get_contents(parser)
        link = u'<a href="%s">' % self.url
        if u'%' in link:
            return link%quote_plus(search.encode("UTF-8"))
        else:
            return link
        
    def render_close(self, parser, node_index):
        
        if self.label:
            ret = u'</a>'
            if self.annotate_links:
                ret += annotate_link(self.label)
            return ret
        else:
            return u''
        
    
class PygmentsCodeTag(TagBase):
    
    def __init__(self, name, pygments_line_numbers=False, **kwargs):
        TagBase.__init__(self, name, enclosed=True, strip_first_newline=True)
        self.line_numbers = pygments_line_numbers
    
    def render_open(self, parser, node_index):
        
        contents = self.get_contents(parser)
        self.skip_contents(parser)
        
        try:
            lexer = get_lexer_by_name(self.params, stripall=True)
        except ClassNotFound:
            contents = _escape(contents)                
            return '<div class="code"><pre>%s</pre></div>' % contents
        
        formatter = HtmlFormatter(linenos=self.line_numbers, cssclass="code")        
        return highlight(contents, lexer, formatter)
        

    
class CodeTag(TagBase):
    
    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, enclosed=True, strip_first_newline=True)        
    
    def render_open(self, parser, node_index):        
        
        contents = _escape(self.get_contents(parser))        
        self.skip_contents(parser)
        return '<div class="code"><pre>%s</pre></div>' % contents

 
class ImgTag(TagBase):
    
    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True) 
    
    def render_open(self, parser, node_index):
        
        contents = self.get_contents(parser)
        self.skip_contents(parser)
        
        contents = strip_bbcode(contents).replace(u'"', "%22")
        
        return u'<img src="%s"></img>' % contents


class ListTag(TagBase):
    
    def __init__(self, name,  **kwargs):
        TagBase.__init__(self, name, strip_first_newline=True)
    
    def open(self, parser, params, open_pos, node_index):
        TagBase.open(self, parser, params, open_pos, node_index)    
    
    def close(self, parser, close_pos, node_index):
        TagBase.close(self, parser, close_pos, node_index)
    
        
    def render_open(self, parser, node_index):        
        
        self.close_tag = u""
        
        tag_data = parser.tag_data
        tag_data.setdefault("ListTag.count", 0)        
        
        if tag_data["ListTag.count"]:
            return u""        
        
        tag_data["ListTag.count"] += 1
                         
        tag_data["ListItemTag.initial_item"]=True
                         
        if self.params == "1":
            self.close_tag = u"</li></ol>"
            return u"<ol><li>"
        elif self.params == "a":
            self.close_tag = u"</li></ol>"
            return u'<ol style="list-style-type: lower-alpha;"><li>'
        elif self.params == "A":
            self.close_tag = u"</li></ol>"
            return u'<ol style="list-style-type: upper-alpha;"><li>'
        else:
            self.close_tag = u"</li></ul>"
            return u"<ul><li>"
        
    def render_close(self, parser, node_index):
                        
        tag_data = parser.tag_data        
        tag_data["ListTag.count"] -= 1 
        
        return self.close_tag


class ListItemTag(TagBase):
    
    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name) 
        self.closed = False       
    
    def render_open(self, parser, node_index):
        
        tag_data = parser.tag_data
        if not tag_data.setdefault("ListTag.count", 0):
            return u""        
        
        if tag_data["ListItemTag.initial_item"]:
            tag_data["ListItemTag.initial_item"] = False
            return
                
        return u"</li><li>"
                

class SizeTag(TagBase):
    
    valid_chars = frozenset("0123456789")
    
    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)
    
    def render_open(self, parser, node_index):
        
        try:
            self.size = int( "".join([c for c in self.params if c in self.valid_chars]) )            
        except ValueError:
            self.size = None
            
        if self.size is None:
            return u""
        
        self.size = self.validate_size(self.size)
        
        return u'<span style="font-size:%spx">' % self.size
    
    def render_close(self, parser, node_index):
        
        if self.size is None:
            return u""
        
        return u'</span>'
    
    def validate_size(self, size):
        
        size = min(64, size)
        size = max(4, size)
        return size


class ColorTag(TagBase):
    
    valid_chars = frozenset("#0123456789abcdefghijklmnopqrstuvwxyz")
    
    def __init__(self, name, **kwargs):
        TagBase.__init__(self, name, inline=True)
    
    def render_open(self, parser, node_index):
        
        valid_chars = self.valid_chars
        color = self.params.split()[0:1][0].lower()        
        self.color = "".join([c for c in color if c in valid_chars])        
        
        if not self.color:
            return u""
        
        return u'<span style="color:%s">' % self.color
        
    def render_close(self, parser, node_index):
        
        if not self.color:
            return u''
        return u'</span>'
        

class CenterTag(TagBase):
        
    def render_open(self, parser, node_index, **kwargs):
                        
        return u'<div style="text-align:center">'
        
        
    def render_close(self, parser, node_index):
                
        return u'</div>'

# http://effbot.org/zone/python-replace.htm
class MultiReplace:

    def __init__(self, repl_dict):
        
        # string to string mapping; use a regular expression
        keys = repl_dict.keys()
        keys.sort() # lexical order
        keys.reverse() # use longest match first
        pattern = u"|".join([re.escape(key) for key in keys])
        self.pattern = re.compile(pattern)
        self.dict = repl_dict

    def replace(self, s):
        # apply replacement dictionary to string

        def repl(match, get=self.dict.get):
            item = match.group(0)
            return get(item, item)
        return self.pattern.sub(repl, s)
    
    __call__ = replace
    
        
def _escape(s):
    return PostMarkup.standard_replace(s.rstrip('\n'))


class TagFactory(object):
    
    def __init__(self):
        
        self.tags = {}
    
    @classmethod
    def tag_factory_callable(cls, tag_class, name, *args, **kwargs):
        """
        Returns a callable that returns a new tag instance.
        """
        def make():            
            return tag_class(name, *args, **kwargs)

        return make
    
    
    def add_tag(self, cls, name, *args, **kwargs):
        
        self.tags[name] = self.tag_factory_callable(cls, name, *args, **kwargs)
        
    def __getitem__(self, name):
        
        return self.tags[name]()
    
    def __contains__(self, name):
        
        return name in self.tags
    
    def get(self, name, default=None):
        
        if name in self.tags:
            return self.tags[name]()
        
        return default        

 
class _Parser(object):
    
    """ This is an interfaced to the parser, used by Tag classes. """
    
    def __init__(self, post_markup):
        
        self.pm = post_markup
        self.tag_data = {}
        self.render_node_index = 0
        
    def skip_to_node(self, node_index):
        
        """ Skips to a node, ignoring intermediate nodes. """ 
        assert node_index is not None, "Node index must be non-None"
        self.render_node_index = node_index
        
    def get_text_nodes(self, node1, node2):
        
        """ Retrieves the text nodes between two node indices. """
        
        if node2 is None:
            node2 = node1+1
        
        return [node for node in self.nodes[node1:node2] if not callable(node)]    
                   
    def begin_no_breaks(self):
        
        """Disables replacing of newlines with break tags at the start and end of text nodes. 
        Can only be called from a tags 'open' method.
        
        """ 
        assert self.phase==1, "Can not be called from render_open or render_close"
        self.no_breaks_count += 1
        
    def end_no_breaks(self):
        
        """Re-enables auto-replacing of newlines with break tags (see begin_no_breaks)."""
        
        assert self.phase==1, "Can not be called from render_open or render_close"
        if self.no_breaks_count:
            self.no_breaks_count -= 1
        
 
class PostMarkup(object):

    standard_replace = MultiReplace({   u'<':u'&lt;',
                                        u'>':u'&gt;',
                                        u'&':u'&amp;',
                                        u'\n':u'<br/>'})

    standard_replace_no_break = MultiReplace({  u'<':u'&lt;',
                                                u'>':u'&gt;',
                                                u'&':u'&amp;',})

    TOKEN_TAG, TOKEN_PTAG, TOKEN_TEXT = range(3)


    # I tried to use RE's. Really I did.
    @classmethod
    def tokenize(cls, post):        

        text = True
        pos = 0

        def find_first(post, pos, c):
            f1 = post.find(c[0], pos)
            f2 = post.find(c[1], pos)
            if f1 == -1:
                return f2
            if f2 == -1:
                return f1
            return min(f1, f2)

        while True:

            brace_pos = post.find(u'[', pos)
            if brace_pos == -1:
                if pos<len(post):
                    yield PostMarkup.TOKEN_TEXT, post[pos:], pos, len(post)
                return
            if brace_pos - pos > 0:
                yield PostMarkup.TOKEN_TEXT, post[pos:brace_pos], pos, brace_pos

            pos = brace_pos
            end_pos = pos+1

            open_tag_pos = post.find(u'[', end_pos)
            end_pos = find_first(post, end_pos, u']=')
            if end_pos == -1:
                yield PostMarkup.TOKEN_TEXT, post[pos:], pos, len(post)
                return
            
            if open_tag_pos != -1 and open_tag_pos < end_pos:                
                yield PostMarkup.TOKEN_TEXT, post[pos:open_tag_pos], pos, open_tag_pos
                end_pos = open_tag_pos
                pos = end_pos
                continue

            if post[end_pos] == ']':
                yield PostMarkup.TOKEN_TAG, post[pos:end_pos+1], pos, end_pos+1
                pos = end_pos+1
                continue

            if post[end_pos] == '=':
                try:
                    end_pos += 1
                    while post[end_pos] == ' ':
                        end_pos += 1
                    if post[end_pos] != '"':
                        end_pos = post.find(u']', end_pos+1)
                        if end_pos == -1:
                            return
                        yield PostMarkup.TOKEN_TAG, post[pos:end_pos+1], pos, end_pos+1
                    else:
                        end_pos = find_first(post, end_pos, u'"]')
                        if end_pos==-1:
                            return
                        if post[end_pos] == '"':
                            end_pos = post.find(u'"', end_pos+1)
                            if end_pos == -1:
                                return
                            end_pos = post.find(u']', end_pos+1)
                            if end_pos == -1:
                                return
                            yield PostMarkup.TOKEN_PTAG, post[pos:end_pos+1], pos, end_pos+1
                        else:
                            yield PostMarkup.TOKEN_TAG, post[pos:end_pos+1], pos, end_pos
                    pos = end_pos+1
                except IndexError:
                    return

    def tagify_urls(self, postmarkup ):
        
        """ Surrounds urls with url bbcode tags. """
        
        def repl(match):            
            return u'[url]%s[/url]' % match.group(0)
        
        text_tokens = []
        for tag_type, tag_token, start_pos, end_pos in self.tokenize(postmarkup):                        
                        
            if tag_type == PostMarkup.TOKEN_TEXT:                
                text_tokens.append(re_url.sub(repl, tag_token))
            else:
                text_tokens.append(tag_token)
                
        return u"".join(text_tokens)


    def __init__(self, tag_factory=None):

        self.tag_factory = tag_factory or TagFactory()


    def default_tags(self):
        
        """ Add some basic tags. """
        
        add_tag = self.tag_factory.add_tag
        
        add_tag(SimpleTag, u'b', u'strong')
        add_tag(SimpleTag, u'i', u'em')
        add_tag(SimpleTag, u'u', u'u')
        add_tag(SimpleTag, u's', u's')


    def get_supported_tags(self):
        
        """ Returns a list of the supported tags. """
        
        return sorted(self.tag_factory.tags.keys())
        


    def render_to_html(self,
                       post_markup,
                       encoding="ascii",
                       exclude_tags=None,
                       auto_urls=True):
        
        """Converts Post Markup to XHTML.

        post_markup -- String containing bbcode.
        encoding -- Encoding of string, defaults to "ascii".
        exclude_tags -- A collection of tag names to ignore.
        auto_urls -- If True, then urls will be wrapped with url bbcode tags.

        """
        
        if not isinstance(post_markup, unicode):
            post_markup = unicode(post_markup, encoding, 'replace') 

        if auto_urls:            
            post_markup = self.tagify_urls(post_markup)                    

        parser = _Parser(self)
        parser.markup = post_markup       
            
        if exclude_tags is None:
            exclude_tags = []
        
        tag_factory = self.tag_factory 
                
           
        nodes = []
        parser.nodes = nodes        
        
        parser.phase = 1
        parser.no_breaks_count = 0
        enclosed_count = 0
        open_stack = []
        tag_stack = []
        break_stack = []
        remove_next_newline = False
        
        def check_tag_stack(tag_name):
            
            for tag in reversed(tag_stack):
                if tag_name == tag.name:
                    return True
            return False
        
        def redo_break_stack():
            
            while break_stack:
                tag = break_stack.pop()
                open_tag(tag)
                tag_stack.append(tag)
                
        def break_inline_tags():
            
            while tag_stack:
                if tag_stack[-1].inline:
                    tag = tag_stack.pop()
                    close_tag(tag)
                    break_stack.append(tag)
                else:
                    break            
                
        def open_tag(tag):
            def call(node_index):
                return tag.render_open(parser, node_index)                            
            nodes.append(call)
            
        def close_tag(tag):  
            def call(node_index):
                return tag.render_close(parser, node_index)          
            nodes.append(call)
        
        # Pass 1
        for tag_type, tag_token, start_pos, end_pos in self.tokenize(post_markup):            
                        
            raw_tag_token = tag_token
                                                                        
            if tag_type == PostMarkup.TOKEN_TEXT:                            
                if parser.no_breaks_count:
                    tag_token = tag_token.strip()
                    if not tag_token:
                        continue     
                if remove_next_newline:
                    tag_token = tag_token.lstrip(' ')
                    if tag_token.startswith('\n'):
                        tag_token = tag_token.lstrip(' ')[1:]
                        if not tag_token:
                            continue
                    remove_next_newline = False                  
                    
                if tag_stack and tag_stack[-1].strip_first_newline:
                    tag_token = tag_token.lstrip()        
                    tag_stack[-1].strip_first_newline = False
                    if not tag_stack[-1]:
                        tag_stack.pop()
                        continue
                    
                if not enclosed_count:                
                    redo_break_stack()
                                                                
                nodes.append(self.standard_replace(tag_token))
                continue
            
            elif tag_type == PostMarkup.TOKEN_TAG:
                tag_token = tag_token[1:-1].lstrip()
                if ' ' in tag_token:
                    tag_name, tag_attribs = tag_token.split(u' ', 1)
                    tag_attribs = tag_attribs.strip()
                else:
                    if '=' in tag_token:
                        tag_name, tag_attribs = tag_token.split(u'=', 1)
                        tag_attribs = tag_attribs.strip()
                    else:
                        tag_name = tag_token
                        tag_attribs = u""
            else:
                tag_token = tag_token[1:-1].lstrip()
                tag_name, tag_attribs = tag_token.split(u'=', 1)
                tag_attribs = tag_attribs.strip()[1:-1]
                        
            tag_name = tag_name.strip().lower().split(':')[0]            
            
            end_tag = False
            if tag_name.startswith(u'/'):
                end_tag = True
                tag_name = tag_name[1:]
                                
                
            if enclosed_count and tag_stack[-1].name != tag_name:
                continue
                
            if tag_name in exclude_tags:
                continue
            
            if not end_tag:
                                
                tag = tag_factory.get(tag_name, None)
                if tag is None:
                    continue
                
                redo_break_stack()
                
                if not tag.inline:
                    break_inline_tags()
                                
                tag.open(parser, tag_attribs, end_pos, len(nodes))
                if tag.enclosed:
                    enclosed_count += 1
                tag_stack.append(tag)
                
                open_tag(tag)
                
                if tag.auto_close:
                    tag = tag_stack.pop()
                    tag.close(self, start_pos, len(nodes)-1)
                    close_tag(tag)                                    
                
            else:
                              
               if check_tag_stack(tag_name):
                   while tag_stack[-1].name != tag_name:
                       tag = tag_stack.pop()
                       break_stack.append(tag)
                       close_tag(tag)
                       
                   tag = tag_stack.pop()
                   tag.close(parser, start_pos, len(nodes))
                   if tag.enclosed:
                       enclosed_count -= 1                   
                       
                   close_tag(tag)
                   
                   if not tag.inline:
                       remove_next_newline = True                   
                   
        if tag_stack:
            redo_break_stack()
            while tag_stack:
                tag = tag_stack.pop()
                tag.close(parser, len(post_markup), len(nodes))  
                if tag.enclosed:
                    enclosed_count -= 1              
                close_tag(tag)
              
        parser.phase = 2
        # Pass 2
        parser.nodes = nodes
        
        text = []
        parser.render_node_index = 0
        while parser.render_node_index < len(parser.nodes):
            i = parser.render_node_index        
            node_text = parser.nodes[i]
            if callable(node_text):
                node_text = node_text(i)
            if node_text is not None:
                text.append(node_text)
            parser.render_node_index += 1            
                   
        return u"".join(text)
    
    __call__ = render_to_html
        


       
            
def _tests():

    import sys
    #sys.stdout=open('test.htm', 'w')

    post_markup = create(use_pygments=True)

    tests = []
    print """<link rel="stylesheet" href="code.css" type="text/css" />\n"""

    tests.append(']')
    tests.append('[')
    tests.append(':-[ Hello, [b]World[/b]')

    tests.append("[link=http://www.willmcgugan.com]My homepage[/link]")
    tests.append('[link="http://www.willmcgugan.com"]My homepage[/link]')
    tests.append("[link http://www.willmcgugan.com]My homepage[/link]")
    tests.append("[link]http://www.willmcgugan.com[/link]")

    tests.append(u"[b]Hello André[/b]")
    tests.append(u"[google]André[/google]")
    tests.append("[s]Strike through[/s]")
    tests.append("[b]bold [i]bold and italic[/b] italic[/i]")
    tests.append("[google]Will McGugan[/google]")
    tests.append("[wiki Will McGugan]Look up my name in Wikipedia[/wiki]")

    tests.append("[quote Will said...]BBCode is very cool[/quote]")

    tests.append("""[code python]
# A proxy object that calls a callback when converted to a string
class TagStringify(object):
    def __init__(self, callback, raw):
        self.callback = callback
        self.raw = raw
        r[b]=3
    def __str__(self):
        return self.callback()
    def __repr__(self):
        return self.__str__()
[/code]""")


    tests.append(u"[img]http://upload.wikimedia.org/wikipedia/commons"\
                 "/6/61/Triops_longicaudatus.jpg[/img]")

    tests.append("[list][*]Apples[*]Oranges[*]Pears[/list]")
    tests.append("""[list=1]
    [*]Apples
    [*]Oranges
    are not the only fruit
    [*]Pears
[/list]""")
    tests.append("[list=a][*]Apples[*]Oranges[*]Pears[/list]")
    tests.append("[list=A][*]Apples[*]Oranges[*]Pears[/list]")

    long_test="""[b]Long test[/b]

New lines characters are converted to breaks."""\
"""Tags my be [b]ove[i]rl[/b]apped[/i].

[i]Open tags will be closed.
[b]Test[/b]"""

    tests.append(long_test)

    tests.append("[dict]Will[/dict]")

    tests.append("[code unknownlanguage]10 print 'In yr code'; 20 goto 10[/code]")
        
    tests.append("[url=http://www.google.com/coop/cse?cx=006850030468302103399%3Amqxv78bdfdo]CakePHP Google Groups[/url]")
    tests.append("[url=http://www.google.com/search?hl=en&safe=off&client=opera&rls=en&hs=pO1&q=python+bbcode&btnG=Search]Search for Python BBCode[/url]")
    #tests = []
    # Attempt to inject html in to unicode
    tests.append("[url=http://www.test.com/sfsdfsdf/ter?t=\"></a><h1>HACK</h1><a>\"]Test Hack[/url]")
        
    tests.append('Nested urls, i.e. [url][url]www.becontrary.com[/url][/url], are condensed in to a single tag.')
    
    tests.append(u'[google]ɸβfvθðsz[/google]')    
    
    tests.append(u'[size 30]Hello, World![/size]')    
    
    tests.append(u'[color red]This should be red[/color]')
    tests.append(u'[color #0f0]This should be green[/color]')
    tests.append(u"[center]This should be in the center!")
        
    tests.append('Nested urls, i.e. [url][url]www.becontrary.com[/url][/url], are condensed in to a single tag.')
    
    #tests = []
    tests.append('[b]Hello, [i]World[/b]! [/i]')
    
    tests.append('[b][center]This should be centered![/center][/b]')
    
    tests.append('[list][*]Hello[i][*]World![/i][/list]')
        
    
    tests.append("""[list=1]
    [*]Apples
    [*]Oranges
    are not the only fruit
    [*]Pears
[/list]""")
        
    tests.append("[b]urls such as http://www.willmcgugan.com are authomaticaly converted to links[/b]")

    tests = []
    tests.append("""
[b]
[code python]
parser.markup[self.open_pos:self.close_pos]
[/code]
asdasdasdasdqweqwe
""")

    tests = ["""[list 1]
[*]Hello
[*]World
[/list]"""]

    for test in tests:
        print u"<pre>%s</pre>"%str(test.encode("ascii", "xmlcharrefreplace"))
        print u"<p>%s</p>"%str(post_markup(test).encode("ascii", "xmlcharrefreplace"))
        print u"<hr/>"
        print

    
    #print render_bbcode("[b]For the lazy, use the http://www.willmcgugan.com render_bbcode function.[/b]")
    

def _run_unittests():
    
    # TODO: Expand tests for better coverage!
    
    import unittest
    
    class TestPostmarkup(unittest.TestCase):
        
        def testsimpletag(self):
            
            postmarkup = create()            
                        
            tests= [ ('[b]Hello[/b]', "<strong>Hello</strong>"),
                     ('[i]Italic[/i]', "<em>Italic</em>"),
                     ('[s]Strike[/s]', "<strike>Strike</strike>"),
                     ('[u]underlined[/u]', "<u>underlined</u>"),
                     ]
            
            for test, result in tests:
                self.assertEqual(postmarkup(test), result)
                    
            
        def testoverlap(self):
            
            postmarkup = create()
                        
            tests= [ ('[i][b]Hello[/i][/b]', "<em><strong>Hello</strong></em>"),
                     ('[b]bold [u]both[/b] underline[/u]', '<strong>bold <u>both</u></strong><u> underline</u>')
                     ]
            
            for test, result in tests:
                self.assertEqual(postmarkup(test), result)
                
        def testlinks(self):
            
            postmarkup = create(annotate_links=False)
                        
            tests= [ ('[link=http://www.willmcgugan.com]blog1[/link]', '<a href="http://www.willmcgugan.com">blog1</a>'),
                     ('[link="http://www.willmcgugan.com"]blog2[/link]', '<a href="http://www.willmcgugan.com">blog2</a>'),
                     ('[link http://www.willmcgugan.com]blog3[/link]', '<a href="http://www.willmcgugan.com">blog3</a>'),
                     ('[link]http://www.willmcgugan.com[/link]', '<a href="http://www.willmcgugan.com">http://www.willmcgugan.com</a>')
                     ]
            
            for test, result in tests:                
                self.assertEqual(postmarkup(test), result)
                
                        
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPostmarkup)
    unittest.TextTestRunner(verbosity=2).run(suite)

        


if __name__ == "__main__":

    #_tests()
    _run_unittests()
