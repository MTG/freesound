from urllib.parse import urlencode

from django import template
from django.urls import reverse
from oauth2_provider.forms import AllowForm

register = template.Library()


@register.simple_tag
def next_url_for_login(form: AllowForm) -> str:
    """Log in as another user needs to pass all authorization request parameters through
    the logout flow and back into the login flow."""
    authorization_fields = (
        "client_id",
        "response_type",
        "redirect_uri",
        "scope",
        "state",
        "code_challenge",
        "code_challenge_method",
    )
    parameters = [(name, form[name].value()) for name in authorization_fields if form[name].value() is not None]
    return f"{reverse('oauth2_provider:authorize')}?{urlencode(parameters)}"
