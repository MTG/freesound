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

from django import template
import urllib, json
from django.conf import settings

register = template.Library()

class PledgieParserNode(template.Node):
    def __init__(self, var_name, pledgie_id=None, pledgie_id_var_name=None):
        self.pledgie_id = pledgie_id
        self.pledgie_id_var_name = pledgie_id_var_name
        self.var_name = var_name

    def render(self, context):
        pledgie_id = None

        if self.pledgie_id_var_name:
            try:
                pledgie_id = int(context[self.pledgie_id_var_name])
            except KeyError:
                raise template.TemplateSyntaxError, "the variable \"%s\" can't be found in the context" % self.pledgie_id_var_name
            except ValueError:
                raise template.TemplateSyntaxError, "pledgie campaign id's need to be integers!"
        else:
            pledgie_id = int(self.pledgie_id)

        api_url = "http://pledgie.com/campaigns/%d.json" % pledgie_id
        pledge_url = "http://pledgie.com/campaigns/%d/" % pledgie_id

        data = None

        try:
            data = json.loads(urllib.urlopen(api_url, proxies=settings.PROXIES).read(), "utf-8")
            data["to_go"] = int(data["campaign"]["goal"] - data["campaign"]["amount_raised"])
            data["url"] = pledge_url
        #except UnicodeDecodeError:
        #    pass
        except:
            data = {}
            data['to_go'] = 0
            data['url'] = 'unknown'

        context[self.var_name] = data

        return ''

import re

@register.tag(name="get_pledgie_campaign_details")
def get_pledgie_campaign_details(parser, token):
    # This version uses a regular expression to parse tag contents.
    try:
        # Splitting by None == splitting by spaces.
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents.split()[0]

    m = re.search(r'(.*?) as (\w+)', arg)
    if not m:
        raise template.TemplateSyntaxError, "%r tag had invalid arguments" % tag_name
    pledgie_id, var_name = m.groups()

    if pledgie_id[0] == pledgie_id[-1] and pledgie_id[0] in ('"', "'"):
        try:
            pledgie_id = int(pledgie_id[1:-1])
        except ValueError:
            raise template.TemplateSyntaxError, "the pledgie id should be an integer..."

        return PledgieParserNode(var_name, pledgie_id=pledgie_id)
    else:
        return PledgieParserNode(var_name, pledgie_id_var_name=pledgie_id)
