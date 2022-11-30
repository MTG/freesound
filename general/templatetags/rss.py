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

from future.utils import raise_
from django import template
import feedparser
import urllib2


register = template.Library()

class RssParserNode(template.Node):
    def __init__(self, var_name, url=None, url_var_name=None):
        self.url = url
        self.url_var_name = url_var_name
        self.var_name = var_name

    def render(self, context):
        proxy = urllib2.ProxyHandler({})
        if self.url:
            context[self.var_name] = feedparser.parse(self.url, handlers=[proxy])
        else:
            try:
                context[self.var_name] = feedparser.parse(context[self.url_var_name], handlers=[proxy])
            except KeyError:
                raise_(template.TemplateSyntaxError, "the variable \"%s\" can't be found in the context" % self.url_var_name)
        return ''

import re

@register.tag(name="get_rss")
def get_rss(parser, token):
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise_(template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0])
    
    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise_(template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name)
    url, var_name = m.groups()
    
    if url[0] == url[-1] and url[0] in ('"', "'"):
        return RssParserNode(var_name, url=url[1:-1])
    else:
        return RssParserNode(var_name, url_var_name=url)
