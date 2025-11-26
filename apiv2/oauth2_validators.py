from oauth2_provider.models import AbstractApplication, Grant
from oauth2_provider.oauth2_validators import GRANT_TYPE_MAPPING
from oauth2_provider.oauth2_validators import OAuth2Validator as ProviderOauth2Validator


class OAuth2Validator(ProviderOauth2Validator):
    def confirm_redirect_uri(self, client_id, code, redirect_uri, client, *args, **kwargs):
        """
        We overwrite this method to make sure that default redirect_uri is taken if no
        redirect_uri is specified in the access token request
        """
        grant = Grant.objects.select_related("application").get(code=code, application=client)
        if redirect_uri is None:
            redirect_uri = grant.application.default_redirect_uri
        return grant.redirect_uri_allowed(redirect_uri)

    def validate_grant_type(self, client_id, grant_type, client, request, *args, **kwargs):
        """
        We overwrite this method because we enable password grant (in addition to authorization code
        grant) based on a boolean in ApiV2Client model. By default, django oauth toolkit only allows
        you to define one allowed authorization grant type per client. Therefore we need to customise
        this method.
        """
        assert grant_type in GRANT_TYPE_MAPPING  # mapping misconfiguration
        if grant_type == AbstractApplication.GRANT_PASSWORD:
            if request.client.apiv2_client.allow_oauth_password_grant:
                return True
        return request.client.authorization_grant_type in GRANT_TYPE_MAPPING[grant_type]
