from oauth2_provider.models import Grant
from oauth2_provider.oauth2_validators import OAuth2Validator as ProviderOauth2Validator

class OAuth2Validator(ProviderOauth2Validator):

    def confirm_redirect_uri(self, client_id, code, redirect_uri, client, *args, **kwargs):
        """
        Ensure the redirect_uri is listed in the Application instance redirect_uris field
        """
        grant = Grant.objects.select_related('application').get(code=code, application=client)
        if redirect_uri is None:
            redirect_uri = grant.application.default_redirect_uri
        return grant.redirect_uri_allowed(redirect_uri)

