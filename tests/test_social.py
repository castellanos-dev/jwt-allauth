"""
Social login.

Covers the two credential flows (a token minted by the provider, and an authorization
code exchanged server side), what happens when the address a provider vouches for
already belongs to somebody, connecting and disconnecting providers, and the gates a
social login shares with the password login -- the second factor, an inactive account,
an unconfirmed address.
"""

import json
import sys
from importlib import reload

import responses
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import NoReverseMatch, clear_url_caches, reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from jwt_allauth.constants import EMAIL_VERIFIED_CLAIM, REFRESH_TOKEN_COOKIE
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from tests.mixins import TestsMixin
from tests.socialprovider.views import ACCESS_TOKEN_URL, USERINFO_URL

SOCIAL_EMAIL = 'social.person@world.com'


def profile(sub='provider-uid-1', email=SOCIAL_EMAIL, email_verified=True, **extra):
    data = {'sub': sub, 'given_name': 'John', 'family_name': 'Smith'}
    if email is not None:
        data['email'] = email
        data['email_verified'] = email_verified
    data.update(extra)
    return data


class SocialTestsMixin(TestsMixin):
    """URLs and provider fakes shared by every social test."""

    def init_social(self):
        self.init()
        self.token_login_url = reverse('jwt_allauth_social_token_login', kwargs={'provider': 'dummy'})
        self.code_login_url = reverse('jwt_allauth_social_code_login', kwargs={'provider': 'dummy'})
        self.token_connect_url = reverse('jwt_allauth_social_token_connect', kwargs={'provider': 'dummy'})
        self.accounts_url = reverse('jwt_allauth_social_accounts')
        self.providers_url = reverse('jwt_allauth_social_providers')

    def tearDown(self):
        cache.clear()

    @staticmethod
    def fake_profile(data=None, status_code=200):
        responses.add(
            responses.GET,
            USERINFO_URL,
            body=json.dumps(data if data is not None else profile()),
            status=status_code,
            content_type='application/json',
        )

    @staticmethod
    def fake_token_exchange(access_token='provider-access-token'):
        responses.add(
            responses.POST,
            ACCESS_TOKEN_URL,
            body=json.dumps({'access_token': access_token, 'token_type': 'bearer'}),
            status=200,
            content_type='application/json',
        )

    def token_payload(self, **overrides):
        payload = {'id_token': 'provider-id-token', 'client_id': 'dummy-client'}
        payload.update(overrides)
        return payload


class SocialTokenLoginTests(SocialTestsMixin):
    """``POST /social/<provider>/token/``."""

    def setUp(self):
        self.init_social()

    @responses.activate
    def test_signs_up_and_opens_a_session(self):
        """A provider account nobody has seen before becomes a user with a session."""
        self.fake_profile()

        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        self.assertIn('access', resp)
        self.assertIn(REFRESH_TOKEN_COOKIE, self.response.cookies)

        user = get_user_model().objects.get(email=SOCIAL_EMAIL)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(EmailAddress.objects.filter(user=user, email=SOCIAL_EMAIL, verified=True).exists())
        self.assertTrue(SocialAccount.objects.filter(user=user, provider='dummy', uid='provider-uid-1').exists())

        # The session is a session like any other: on the whitelist, so that logout and
        # rotation can see it.
        row = RefreshTokenWhitelistModel.objects.get(user=user)
        self.assertTrue(row.enabled)
        self.assertTrue(row.session)

        self.assertTrue(AccessToken(resp['access'])[EMAIL_VERIFIED_CLAIM])

    @responses.activate
    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
    def test_records_the_device_the_session_was_opened_from(self):
        """
        Proves ``@get_user_agent`` is on the handler: without it the whole flow still
        works and the session simply lands with no device on it.
        """
        self.fake_profile()

        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK,
                  HTTP_USER_AGENT='Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0')

        row = RefreshTokenWhitelistModel.objects.get(user__email=SOCIAL_EMAIL)
        self.assertEqual(row.browser, 'Chrome')
        self.assertTrue(row.is_pc)

    @responses.activate
    def test_second_login_reuses_the_account(self):
        """The same provider account does not become a second user."""
        self.fake_profile()
        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)
        count = get_user_model().objects.count()

        self.fake_profile()
        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        self.assertEqual(get_user_model().objects.count(), count)
        self.assertEqual(SocialAccount.objects.filter(provider='dummy').count(), 1)

    @responses.activate
    def test_unknown_provider_is_not_found(self):
        url = reverse('jwt_allauth_social_token_login', kwargs={'provider': 'nowhere'})
        resp = self.post(url, data=self.token_payload(), status_code=status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp['code'], 'provider_not_configured')

    @responses.activate
    def test_provider_without_token_flow_is_refused(self):
        url = reverse('jwt_allauth_social_token_login', kwargs={'provider': 'notoken'})
        resp = self.post(url, data=self.token_payload(client_id='notoken-client'),
                         status_code=status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp['code'], 'flow_not_supported')

    @responses.activate
    def test_credential_of_another_client_is_refused(self):
        """
        A bearer token minted for a different application of the same provider is not
        proof of identity here.
        """
        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(client_id='somebody-elses-client'),
                         status_code=status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp['code'], 'client_id_mismatch')
        self.assertFalse(SocialAccount.objects.exists())

    @responses.activate
    def test_missing_client_id_is_refused(self):
        self.fake_profile()
        resp = self.post(self.token_login_url, data={'id_token': 'provider-id-token'},
                         status_code=status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp['code'], 'client_id_mismatch')

    def test_body_without_a_credential_is_rejected(self):
        self.post(self.token_login_url, data={'client_id': 'dummy-client'},
                  status_code=status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_provider_rejecting_the_credential_creates_nothing(self):
        self.fake_profile(status_code=400)
        count = get_user_model().objects.count()

        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(resp['code'], 'invalid_social_token')
        self.assertEqual(get_user_model().objects.count(), count)

    @responses.activate
    def test_unverified_provider_address_creates_nothing(self):
        """An address nobody vouched for is a dead end: no password to reset it with."""
        self.fake_profile(profile(email_verified=False))
        count = get_user_model().objects.count()

        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(resp['code'], 'provider_email_unverified')
        self.assertEqual(get_user_model().objects.count(), count)

    @responses.activate
    def test_provider_supplying_no_address_creates_nothing(self):
        self.fake_profile(profile(email=None))
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp['code'], 'provider_email_unverified')

    @responses.activate
    @override_settings(SOCIALACCOUNT_AUTO_SIGNUP=False)
    def test_signup_disabled_is_refused(self):
        """There is no sign-up form to fall back to over an API."""
        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp['code'], 'signup_not_allowed')

    @responses.activate
    @override_settings(JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION=True)
    def test_admin_managed_registration_closes_the_door(self):
        """What the registration endpoint refuses, a provider must not let in."""
        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp['code'], 'signup_closed')

    @responses.activate
    def test_inactive_account_is_refused(self):
        self.fake_profile()
        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)
        get_user_model().objects.filter(email=SOCIAL_EMAIL).update(is_active=False)

        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_401_UNAUTHORIZED)

        # Word for word what `/login/` answers for an inactive account: the two ways in
        # must not be told apart by their refusals.
        self.assertEqual(resp['detail'], 'No active account found with the given credentials')


class SocialEmailLinkingTests(SocialTestsMixin):
    """
    What happens when the address a provider vouches for is already somebody's.

    This is the decision the feature exists for: an account whose address was confirmed
    belongs to its owner, and a provider vouching for the same address is that same
    person -- so the provider is connected and the password left alone.
    """

    def setUp(self):
        self.init_social()

    @responses.activate
    def test_links_to_a_claimed_account_and_keeps_the_password(self):
        self.fake_profile(profile(email=self.EMAIL))
        user_count = get_user_model().objects.count()

        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        self.assertIn('access', resp)
        self.assertEqual(get_user_model().objects.count(), user_count)

        account = SocialAccount.objects.get(provider='dummy')
        self.assertEqual(account.user_id, self.USER.id)

        self.USER.refresh_from_db()
        self.assertTrue(self.USER.has_usable_password())

        # And the password still opens a session: adding a provider is not a migration
        # away from the password.
        self._login()

    @responses.activate
    def test_a_second_provider_reaches_the_same_account(self):
        self.fake_profile(profile(email=self.EMAIL))
        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        second_url = reverse('jwt_allauth_social_token_login', kwargs={'provider': 'second'})
        self.fake_profile(profile(sub='second-uid', email=self.EMAIL))
        self.post(second_url, data=self.token_payload(client_id='second-client'), status_code=status.HTTP_200_OK)

        self.assertEqual(
            sorted(SocialAccount.objects.filter(user=self.USER).values_list('provider', flat=True)),
            ['dummy', 'second'],
        )

    @responses.activate
    def test_supersedes_an_account_nobody_ever_claimed(self):
        """
        A sign-up that was never confirmed and never used could have been made by
        anyone, with anyone's address. It goes, exactly as registration makes it go.
        """
        stranger = get_user_model().objects.create_user('stranger', email=SOCIAL_EMAIL, password='Val1dPasw0rd')
        EmailAddress.objects.create(user=stranger, email=SOCIAL_EMAIL, verified=False, primary=True)

        self.fake_profile()
        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        self.assertFalse(get_user_model().objects.filter(pk=stranger.pk).exists())
        account = SocialAccount.objects.get(provider='dummy')
        self.assertEqual(account.user.email, SOCIAL_EMAIL)
        self.assertFalse(account.user.has_usable_password())

    @responses.activate
    @override_settings(JWT_ALLAUTH_SOCIAL_EMAIL_LINKING=False)
    def test_linking_switched_off_reports_the_conflict(self):
        self.fake_profile(profile(email=self.EMAIL))

        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_409_CONFLICT)

        self.assertEqual(resp['code'], 'email_already_registered')
        self.assertFalse(SocialAccount.objects.exists())

    @responses.activate
    @override_settings(JWT_ALLAUTH_SOCIAL_EMAIL_LINKING=['second'])
    def test_linking_can_be_allowed_per_provider(self):
        """The trust is in the provider, not in the mechanism."""
        self.fake_profile(profile(email=self.EMAIL))
        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_409_CONFLICT)

        second_url = reverse('jwt_allauth_social_token_login', kwargs={'provider': 'second'})
        self.fake_profile(profile(sub='second-uid', email=self.EMAIL))
        self.post(second_url, data=self.token_payload(client_id='second-client'), status_code=status.HTTP_200_OK)

    @responses.activate
    @override_settings(EMAIL_VERIFICATION='mandatory')
    def test_unconfirmed_local_account_is_refused_as_it_would_be_with_a_password(self):
        user = get_user_model().objects.create_user('pending', email=SOCIAL_EMAIL, password='Val1dPasw0rd')
        user.last_login = None
        user.save()
        EmailAddress.objects.create(user=user, email=SOCIAL_EMAIL, verified=False, primary=True)
        SocialAccount.objects.create(user=user, provider='dummy', uid='provider-uid-1')

        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(resp['code'], 'email_not_verified')


class SocialCodeLoginTests(SocialTestsMixin):
    """``POST /social/<provider>/code/``."""

    def setUp(self):
        self.init_social()

    def code_payload(self, **overrides):
        payload = {'code': 'auth-code', 'callback_url': 'https://app.test/callback'}
        payload.update(overrides)
        return payload

    @responses.activate
    def test_exchanges_the_code_and_opens_a_session(self):
        self.fake_token_exchange()
        self.fake_profile()

        resp = self.post(self.code_login_url, data=self.code_payload(), status_code=status.HTTP_200_OK)

        self.assertIn('access', resp)
        self.assertTrue(SocialAccount.objects.filter(provider='dummy').exists())

    @responses.activate
    def test_forwards_the_pkce_verifier(self):
        self.fake_token_exchange()
        self.fake_profile()

        self.post(self.code_login_url, data=self.code_payload(code_verifier='the-verifier'),
                  status_code=status.HTTP_200_OK)

        exchange = next(c for c in responses.calls if c.request.url.startswith(ACCESS_TOKEN_URL))
        self.assertIn('code_verifier=the-verifier', exchange.request.body)

    @responses.activate
    def test_provider_refusing_the_exchange_creates_nothing(self):
        responses.add(responses.POST, ACCESS_TOKEN_URL, body='{"error": "invalid_grant"}',
                      status=400, content_type='application/json')
        count = get_user_model().objects.count()

        resp = self.post(self.code_login_url, data=self.code_payload(), status_code=status.HTTP_401_UNAUTHORIZED)

        self.assertEqual(resp['code'], 'invalid_social_token')
        self.assertEqual(get_user_model().objects.count(), count)

    @responses.activate
    @override_settings(JWT_ALLAUTH_SOCIAL_CALLBACK_URLS=['https://app.test/callback'])
    def test_callback_url_outside_the_allow_list_is_refused(self):
        resp = self.post(self.code_login_url, data=self.code_payload(callback_url='https://evil.test/callback'),
                         status_code=status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp['code'], 'callback_url_not_allowed')

    def test_code_is_required(self):
        self.post(self.code_login_url, data={'callback_url': 'https://app.test/callback'},
                  status_code=status.HTTP_400_BAD_REQUEST)


class SocialConnectTests(SocialTestsMixin):
    """Connecting, listing and disconnecting providers."""

    def setUp(self):
        self.init_social()

    @responses.activate
    def test_connecting_requires_a_session(self):
        self.fake_profile()
        self.post(self.token_connect_url, data=self.token_payload(), status_code=status.HTTP_401_UNAUTHORIZED)

    @responses.activate
    def test_connecting_adds_the_provider_without_opening_a_session(self):
        self._login()
        sessions = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()

        self.fake_profile()
        resp = self.post(self.token_connect_url, data=self.token_payload(), status_code=status.HTTP_201_CREATED)

        self.assertEqual(resp['provider'], 'dummy')
        self.assertNotIn('access', resp)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, self.response.cookies)
        self.assertEqual(RefreshTokenWhitelistModel.objects.filter(user=self.USER).count(), sessions)

        # A provider must not graft its own address onto an account that did not ask.
        self.assertFalse(EmailAddress.objects.filter(user=self.USER, email=SOCIAL_EMAIL).exists())

    @responses.activate
    def test_connecting_twice_is_idempotent(self):
        self._login()
        self.fake_profile()
        self.post(self.token_connect_url, data=self.token_payload(), status_code=status.HTTP_201_CREATED)
        self.fake_profile()
        self.post(self.token_connect_url, data=self.token_payload(), status_code=status.HTTP_201_CREATED)

        self.assertEqual(SocialAccount.objects.filter(user=self.USER).count(), 1)

    @responses.activate
    def test_connecting_somebody_elses_provider_account_is_refused(self):
        other = get_user_model().objects.create_user('other', email='other@world.com', password='Val1dPasw0rd')
        SocialAccount.objects.create(user=other, provider='dummy', uid='provider-uid-1')
        self._login()

        self.fake_profile()
        resp = self.post(self.token_connect_url, data=self.token_payload(), status_code=status.HTTP_409_CONFLICT)

        self.assertEqual(resp['code'], 'social_account_in_use')
        self.assertEqual(SocialAccount.objects.get(uid='provider-uid-1').user_id, other.id)

    def test_list_shows_only_the_callers_accounts(self):
        other = get_user_model().objects.create_user('other', email='other@world.com', password='Val1dPasw0rd')
        SocialAccount.objects.create(user=other, provider='dummy', uid='not-mine')
        mine = SocialAccount.objects.create(user=self.USER, provider='second', uid='mine')
        self._login()

        resp = self.get(self.accounts_url, status_code=status.HTTP_200_OK)

        self.assertEqual([a['id'] for a in resp], [mine.id])
        self.assertNotIn('extra_data', resp[0])

    def test_disconnecting_an_account_of_somebody_else_is_not_found(self):
        other = get_user_model().objects.create_user('other', email='other@world.com', password='Val1dPasw0rd')
        account = SocialAccount.objects.create(user=other, provider='dummy', uid='not-mine')
        self._login()

        url = reverse('jwt_allauth_social_disconnect', kwargs={'pk': account.pk})
        self.delete(url, status_code=status.HTTP_404_NOT_FOUND)
        self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())

    def test_disconnecting_leaves_an_account_that_still_has_a_password(self):
        account = SocialAccount.objects.create(user=self.USER, provider='dummy', uid='mine')
        self._login()

        url = reverse('jwt_allauth_social_disconnect', kwargs={'pk': account.pk})
        self.delete(url, status_code=status.HTTP_204_NO_CONTENT)

        self.assertFalse(SocialAccount.objects.filter(pk=account.pk).exists())

    @responses.activate
    def test_disconnecting_the_only_way_in_is_refused(self):
        """An account born of a provider has no password to fall back to."""
        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)
        self.token = resp['access']

        account = SocialAccount.objects.get(provider='dummy')
        url = reverse('jwt_allauth_social_disconnect', kwargs={'pk': account.pk})

        resp = self.delete(url, status_code=status.HTTP_400_BAD_REQUEST)

        self.assertEqual(resp['code'], 'disconnect_not_allowed')
        self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())


class SocialProviderListTests(SocialTestsMixin):
    """``GET /social/providers/``."""

    def setUp(self):
        self.init_social()

    def test_lists_the_configured_providers_without_the_secret(self):
        resp = self.get(self.providers_url, status_code=status.HTTP_200_OK)

        by_id = {p['id']: p for p in resp}
        self.assertEqual(by_id['dummy']['client_id'], 'dummy-client')
        self.assertNotIn('dummy-secret', json.dumps(resp))
        self.assertNotIn('secret', by_id['dummy'])


@override_settings(JWT_ALLAUTH_MFA_TOTP_MODE='optional')
class SocialMFATests(SocialTestsMixin):
    """
    A provider proves the first factor, not the second.

    Whoever takes over the identity provider account would otherwise walk straight past
    the authenticator this account enrolled.
    """

    def setUp(self):
        self.init_social()

    def enrol(self, user):
        from allauth.mfa.models import Authenticator
        from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret

        secret = generate_totp_secret()
        return TOTP.activate(user, secret) and Authenticator.objects.get(user=user)

    @responses.activate
    def test_enrolled_account_gets_a_challenge_instead_of_a_session(self):
        self.fake_profile()
        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)
        user = get_user_model().objects.get(email=SOCIAL_EMAIL)
        self.enrol(user)

        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        self.assertTrue(resp['mfa_required'])
        self.assertIn('challenge_id', resp)
        self.assertNotIn('access', resp)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, self.response.cookies)

    @responses.activate
    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE='required')
    def test_required_mode_bootstraps_enrolment(self):
        self.fake_profile()
        resp = self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        self.assertTrue(resp['mfa_setup_required'])
        self.assertIn('setup_challenge_id', resp)
        self.assertNotIn('access', resp)


class SocialRoutingTests(SimpleTestCase):
    """
    The social endpoints only exist when the project installs allauth's socialaccount app.

    Its HTTP stack -- ``requests``, ``pyjwt[crypto]`` -- sits behind an extra, so routing
    the views unconditionally would make that extra a hard dependency of every
    installation, social login or not.
    """

    @staticmethod
    def _reload_urls():
        """
        Rebuild the URLconf under the settings in force.

        ``jwt_allauth.registration.urls`` is in the list even though this test does not
        touch registration: dropping an app from ``INSTALLED_APPS`` re-runs every app's
        ``ready()``, and rebuilding only part of the tree leaves the rest pointing at
        module objects that no longer exist -- which showed up as an unrelated endpoint
        answering ``404`` several test classes later.
        """
        clear_url_caches()
        for name in ('jwt_allauth.registration.urls', 'jwt_allauth.urls', settings.ROOT_URLCONF):
            module = sys.modules.get(name)
            if module is not None:
                reload(module)

    def test_routed_when_the_app_is_installed(self):
        self.assertTrue(reverse('jwt_allauth_social_token_login', kwargs={'provider': 'dummy'}))

    def test_not_routed_without_the_app(self):
        without_socialaccount = [app for app in settings.INSTALLED_APPS
                                 if app not in ('allauth.socialaccount', 'tests.socialprovider')]
        try:
            with override_settings(INSTALLED_APPS=without_socialaccount):
                self._reload_urls()
                with self.assertRaises(NoReverseMatch):
                    reverse('jwt_allauth_social_token_login', kwargs={'provider': 'dummy'})
                # The rest of the library is untouched by its absence.
                self.assertTrue(reverse('rest_login'))
        finally:
            self._reload_urls()


@override_settings(SOCIALACCOUNT_EMAIL_AUTHENTICATION=True)
class SocialAllauthEmailAuthenticationTests(SocialTestsMixin):
    """
    allauth's own e-mail matching must not decide what this library decides.

    ``SocialLogin.lookup()`` falls through to matching by address whenever allauth's
    flag is on, and that verdict skips ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING``, skips the
    claimed-account rule, and never records the connection.
    """

    def setUp(self):
        self.init_social()

    @responses.activate
    @override_settings(JWT_ALLAUTH_SOCIAL_EMAIL_LINKING=False)
    def test_allauth_email_matching_does_not_override_linking_off(self):
        self.fake_profile(profile(email=self.EMAIL))

        resp = self.post(self.token_login_url, data=self.token_payload(),
                         status_code=status.HTTP_409_CONFLICT)

        self.assertEqual(resp['code'], 'email_already_registered')
        self.assertFalse(SocialAccount.objects.exists())

    @responses.activate
    def test_linking_still_records_the_connection(self):
        """
        With linking on the answer is the same as without allauth's flag -- and the
        connection is persisted, so it can be listed and disconnected.
        """
        self.fake_profile(profile(email=self.EMAIL))

        self.post(self.token_login_url, data=self.token_payload(), status_code=status.HTTP_200_OK)

        account = SocialAccount.objects.get(provider='dummy')
        self.assertEqual(account.user_id, self.USER.id)
        self.assertIsNotNone(account.pk)

    @responses.activate
    def test_connect_persists_the_account(self):
        """A 201 that stored nothing is worse than a refusal: it reports a lie."""
        self._login()
        self.fake_profile(profile(email=self.EMAIL))

        resp = self.post(self.token_connect_url, data=self.token_payload(),
                         status_code=status.HTTP_201_CREATED)

        self.assertIsNotNone(resp['id'])
        self.assertEqual(SocialAccount.objects.filter(user=self.USER).count(), 1)
