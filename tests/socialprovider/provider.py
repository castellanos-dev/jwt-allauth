"""
A provider that exists only for the tests.

Faking Google or Facebook would mean testing against a moving target maintained
elsewhere. This one is deliberately plain -- it does what the base classes ask for and
nothing else -- so a failure points at this library rather than at somebody's API.

``NoTokenProvider`` is the same thing without ``supports_token_authentication``, which
is how the "this provider cannot do that flow" branch gets exercised.
"""

import requests
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

from tests.socialprovider.views import DummyOAuth2Adapter, fetch_profile


class DummyAccount(ProviderAccount):
    pass


class DummyProvider(OAuth2Provider):
    id = 'dummy'
    name = 'Dummy'
    account_class = DummyAccount
    oauth2_adapter_class = DummyOAuth2Adapter
    supports_token_authentication = True

    def get_default_scope(self):
        return ['email']

    def extract_uid(self, data):
        return str(data['sub'])

    def extract_common_fields(self, data):
        return dict(
            email=data.get('email'),
            first_name=data.get('given_name'),
            last_name=data.get('family_name'),
        )

    def extract_email_addresses(self, data):
        # ``emails`` is this provider's own extension, so that a test can hand over more
        # than one vouched-for address -- which real providers do, and which is what
        # makes the order the resolver reaches its verdict in observable.
        addresses = [
            EmailAddress(email=entry['email'], verified=bool(entry.get('email_verified')))
            for entry in data.get('emails', [])
        ]
        email = data.get('email')
        if email:
            addresses.insert(0, EmailAddress(email=email, verified=bool(data.get('email_verified')), primary=True))
        return addresses

    def verify_token(self, request, token):
        credential = token.get('id_token') or token.get('access_token')
        if not credential:
            raise get_adapter().validation_error('invalid_token')
        try:
            data = fetch_profile(credential)
        except (OAuth2Error, requests.RequestException) as e:
            raise get_adapter().validation_error('invalid_token') from e
        return self.sociallogin_from_response(request, data)


class SecondProvider(DummyProvider):
    """A second provider, to check that two of them can reach the same account."""

    id = 'second'
    name = 'Second'


class NoTokenProvider(DummyProvider):
    id = 'notoken'
    name = 'No Token'
    supports_token_authentication = False


provider_classes = [DummyProvider, SecondProvider, NoTokenProvider]
