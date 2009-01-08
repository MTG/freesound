from django import template
from django.conf import settings
import re

register = template.Library()

replacements = {
    ":)": "happy",
    ":-)": "happy",
    ":s": "oups",
    ":-s": "oups",
    ":d": "extatic",
    ":-d": "extatic",
    ":*": "kiss",
    ":-*": "kiss",
    ":(": "sad",
    ":-(": "sad",
    ":|": "soso",
    ":-|": "soso",
    "8)": "sun",
    "8-)": "sun",
    ":o": "surprise",
    ":-o": "surprise",
    ":p": "tongue",
    ":-p": "tongue",
    ":'(": "cry",
    }

def smiley_replace(matchobj):
    try:
        expression = replacements[matchobj.group(0).lower()]
        return "<img src=\"%simages/smileys/%s.png\" alt=\"%s\" class=\"smiley\" />" % (settings.MEDIA_URL, expression, expression)
    except KeyError:
        return matchobj.group(0)

smiley_replacer = re.compile("8\-?\)|:'\(|:\-?[OoPpSsDd\)\(\*\|]")

@register.filter
def smileys(string):
    return smiley_replacer.sub(smiley_replace, string)
smileys.is_safe = True