from django import template
from django.conf import settings
from django.templatetags.static import static
import re

register = template.Library()

mapping = """8-) 8) cool
:'( cry
:D :-D grin
=) happy
:-| :| neutral
:( :-( sad
:) :-) smile
:P :-P tongue
:S :-S weird
;) ;-) wink
:O :-O woot"""

d = []
for emoticons, name in [(x[:-1], x[-1]) for x in [x.split() for x in mapping.lower().split("\n")]]:
    for emoticon in emoticons:
        d.append((emoticon, name))

emoticons = dict(d)


def smiley_replace(matchobj):
    try:
        expression = emoticons[matchobj.group(0).lower()]
        url = static('bw-frontend/public/smileys/%s.png' % expression)
        return f"<img src=\"{url}\" alt=\"{expression}\" class=\"smiley\" />"
    except KeyError:
        return matchobj.group(0)


smiley_replacer = re.compile(r"=\)|;\-?\)|8\-?\)|:'\(|:\-?[OoPpSsDd\)\(\|]")


@register.filter(is_safe=True)
def smileys(string):
    return smiley_replacer.sub(smiley_replace, string)


#smileys.is_safe = True # Moved to filter definition (for Django 1.4 upgrade)
