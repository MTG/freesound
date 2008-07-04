from django import template
import feedparser

register = template.Library()

class RssParserNode(template.Node):
    def __init__(self, var_name, url=None, url_var_name=None):
        self.url = url
        self.url_var_name = url_var_name
        self.var_name = var_name
    def render(self, context):
        if self.url:
            print 
            context[self.var_name] = feedparser.parse(self.url)
        else:
            context[self.var_name] = feedparser.parse(context[self.url_var_name])
        return ''

import re

@register.tag(name="get_rss")
def get_rss(parser, token):
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]
    
    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name
    url, var_name = m.groups()
    
    if not (url[0] == url[-1] and url[0] in ('"', "'")):
        return RssParserNode(var_name, url_var_name=url)
    else:
        return RssParserNode(var_name, url=url[1:-1])
    