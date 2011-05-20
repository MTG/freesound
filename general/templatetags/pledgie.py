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
        except UnicodeDecodeError:
            pass

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
