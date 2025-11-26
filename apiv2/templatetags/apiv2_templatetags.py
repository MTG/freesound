from urllib.parse import quote

from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def next_url_for_login(client_id, response_type, state):
    return quote(
        "%s?client_id=%s&response_type=%s&state=%s"
        % (reverse("oauth2_provider:authorize"), client_id, response_type, state)
    )
