"""OAuth2 adapter of the provider the social tests run against."""

import requests
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter

USERINFO_URL = 'https://dummy.test/userinfo'
ACCESS_TOKEN_URL = 'https://dummy.test/token'
AUTHORIZE_URL = 'https://dummy.test/authorize'


def fetch_profile(access_token):
    """
    Read the profile the way a real provider makes you: over HTTP.

    Going through ``requests`` is what lets the tests fake the provider with
    ``responses`` rather than stubbing out the library's own code.
    """
    response = requests.get(USERINFO_URL, headers={'Authorization': f'Bearer {access_token}'}, timeout=5)
    if response.status_code != 200:
        raise OAuth2Error('provider rejected the token')
    return response.json()


class DummyOAuth2Adapter(OAuth2Adapter):
    provider_id = 'dummy'
    access_token_url = ACCESS_TOKEN_URL
    authorize_url = AUTHORIZE_URL
    profile_url = USERINFO_URL

    def complete_login(self, request, app, token, **kwargs):
        try:
            data = fetch_profile(token.token)
        except (OAuth2Error, requests.RequestException) as e:
            raise get_adapter().validation_error('invalid_token') from e
        return self.get_provider().sociallogin_from_response(request, data)
