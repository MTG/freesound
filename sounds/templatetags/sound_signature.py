import urllib.parse

from django import template
from django.contrib.sites.models import Site
from django.urls import reverse

register = template.Library()

SOUND_SIGNATURE_SOUND_ID_PLACEHOLDER = "${sound_id}"
SOUND_SIGNATURE_SOUND_URL_PLACEHOLDER = "${sound_url}"


@register.filter(name="sound_signature_replace")
def sound_signature_replace(value, sound):
    domain = f"https://{Site.objects.get_current().domain}"
    abs_url = urllib.parse.urljoin(domain, reverse("sound", args=[sound.user.username, sound.id]))

    replace = [(SOUND_SIGNATURE_SOUND_ID_PLACEHOLDER, str(sound.id)), (SOUND_SIGNATURE_SOUND_URL_PLACEHOLDER, abs_url)]
    for placeholder, v in replace:
        value = value.replace(placeholder, v)
    return value
