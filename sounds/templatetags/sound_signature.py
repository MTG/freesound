import urlparse
from django.urls import reverse
from django.contrib.sites.models import Site
from django import template

register = template.Library()


@register.filter(name='sound_signature_replace')
def sound_signature_replace(value, sound):
    domain = "https://%s" % Site.objects.get_current().domain
    abs_url = urlparse.urljoin(domain, reverse('sound', args=[sound.user.username, sound.id]))

    replace = [("${sound_id}", str(sound.id)),
            ("${sound_url}", abs_url)]
    for placeholder, v in replace:
        value = value.replace(placeholder, v)
    return value
