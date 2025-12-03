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

import urllib.error
import urllib.parse
import urllib.request

import feedparser
from bs4 import BeautifulSoup
from django import template
from django.utils.text import Truncator

register = template.Library()


class RssParserNode(template.Node):
    def __init__(self, var_name, url=None, url_var_name=None):
        self.url = url
        self.url_var_name = url_var_name
        self.var_name = var_name

    def render(self, context):
        proxy = urllib.request.ProxyHandler({})
        if self.url:
            context[self.var_name] = feedparser.parse(self.url, handlers=[proxy])
        else:
            try:
                context[self.var_name] = feedparser.parse(context[self.url_var_name], handlers=[proxy])
            except KeyError:
                raise template.TemplateSyntaxError(f"the variable '{self.url_var_name}' can't be found in the context")

        # Add custom-made summaries with a specific length of 300 chars which are slightly longer that those auto-generated
        # by feedparser.
        for entry in context[self.var_name]["entries"]:
            soup = BeautifulSoup(entry["content"][0]["value"], features="html.parser")
            text_without_html_tags = soup.get_text()
            truncated_text = Truncator(text_without_html_tags).chars(300, truncate="...")
            entry["summary_custom"] = truncated_text
        return ""


import re


@register.tag(name="get_rss")
def get_rss(parser, token):
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError(f"{token.contents.split()[0]!r} tag requires arguments")

    m = re.search(r"(.*?) as (\w+)", arg)
    if not m:
        raise template.TemplateSyntaxError(f"{tag_name!r} tag had invalid arguments")
    url, var_name = m.groups()

    if url[0] == url[-1] and url[0] in ('"', "'"):
        return RssParserNode(var_name, url=url[1:-1])
    else:
        return RssParserNode(var_name, url_var_name=url)
