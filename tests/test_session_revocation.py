import warnings

from django.test import override_settings
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from jwt_allauth.authentication import (
    JWTAllAuthAuthentication,
    SessionRevocationMixin,
    validate_session,
    warn_if_revocation_is_not_enforced,
)
from jwt_allauth.constants import FOR_USER, ONE_TIME_PERMISSION, PASS_RESET_ACCESS, REFRESH_TOKEN_COOKIE
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.tokens import RefreshToken

from .mixins import APIClient, TestsMixin


class SessionRevocationTests(TestsMixin):
    """
    Revoking a session must also stop the access tokens already issued for it.
    """

    def setUp(self):
        self.init()

    def test_access_token_valid_while_session_is_whitelisted(self):
        self.token = self.ACCESS
        self.get(self.user_url, status_code=200)

    def test_access_token_survives_rotation_of_its_session(self):
        """Rotating the refresh token does not invalidate the access tokens already handed out."""
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        self.post(self.refresh_url, data={}, status_code=200)

        self.token = self.ACCESS
        self.get(self.user_url, status_code=200)

    def test_access_token_rejected_after_refresh_token_reuse(self):
        """
        The reported scenario: a refresh token is replayed from a second browser.

        Detecting the reuse revokes the session, which must lock out the browser that
        replayed the token as well — including the access token it just obtained.
        """
        stolen = str(self.TOKEN)

        attacker = APIClient()
        attacker.cookies[REFRESH_TOKEN_COOKIE] = stolen
        response = attacker.post(self.refresh_url, data={}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        attacker_access = response.json()['access']

        # The access token obtained with the stolen refresh token works while the session
        # has not been revoked yet.
        self.assertEqual(
            attacker.get(self.user_url, HTTP_AUTHORIZATION=f'Bearer {attacker_access}').status_code, 200)

        # The legitimate browser refreshes with the token that was already rotated: the
        # reuse is detected and the whole session is revoked.
        victim = APIClient()
        victim.cookies[REFRESH_TOKEN_COOKIE] = stolen
        self.assertEqual(
            victim.post(self.refresh_url, data={}, content_type='application/json').status_code, 401)
        self.assertFalse(
            RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())

        # Both browsers are out: no rotation, and no access with the tokens already issued.
        response = attacker.get(self.user_url, HTTP_AUTHORIZATION=f'Bearer {attacker_access}')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 'token_not_valid')
        self.assertEqual(
            attacker.post(self.refresh_url, data={}, content_type='application/json').status_code, 401)

    def test_access_token_rejected_after_logout(self):
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        self.token = self.ACCESS
        self.post(self.logout_url, data={}, status_code=200)

        self.get(self.user_url, status_code=401)

    def test_access_token_rejected_after_logout_all(self):
        self.token = self.ACCESS
        self.post(self.logout_all_url, data={}, status_code=200)

        self.get(self.user_url, status_code=401)

    def test_access_token_rejected_for_another_revoked_session(self):
        """Revoking one session leaves the other sessions of the same user untouched."""
        other = RefreshToken.for_user(self.USER)
        other_access = str(other.access_token)

        RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).delete()

        self.token = self.ACCESS
        self.get(self.user_url, status_code=401)

        self.token = other_access
        self.get(self.user_url, status_code=200)

    def test_access_token_of_unverified_account_is_accepted(self):
        """
        Tokens whitelisted as disabled (email not verified) are rejected on rotation, not
        on authentication, so the verification endpoints stay reachable.
        """
        token_object = RefreshTokenWhitelistModel.objects.get(jti=self.TOKEN.payload['jti'])
        token_object.enabled = False
        token_object.save()

        self.token = self.ACCESS
        self.get(self.user_url, status_code=200)

    def test_token_without_session_claim_is_not_checked(self):
        """One-time capability tokens carry no session and must not be rejected here."""
        one_time = RefreshToken()
        one_time[FOR_USER] = self.USER.id
        one_time[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = one_time.access_token

        self.assertNotIn('session', access_token.payload)
        validate_session(access_token)  # does not raise

    def test_refresh_rejects_a_token_without_session_claim(self):
        """A signed refresh token that carries no session is rejected, not a server error."""
        token = RefreshToken.for_user(self.USER)
        del token.payload['session']

        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(token)
        response = self.post(self.refresh_url, data={}, status_code=401)
        self.assertEqual(response['code'], 'token_not_valid')

    @override_settings(JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK=False)
    def test_session_check_can_be_disabled(self):
        """Opting out restores fully stateless authentication."""
        RefreshTokenWhitelistModel.objects.all().delete()

        self.token = self.ACCESS
        self.get(self.user_url, status_code=200)

    def test_default_authentication_class_enforces_revocation(self):
        from django.conf import settings

        self.assertIn(
            'jwt_allauth.authentication.JWTAllAuthAuthentication',
            settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'],
        )
        self.assertTrue(issubclass(JWTAllAuthAuthentication, SessionRevocationMixin))
        self.assertTrue(issubclass(JWTAllAuthAuthentication, JWTStatelessUserAuthentication))

    def test_warning_when_revocation_is_not_enforced(self):
        rest_framework_settings = {
            'DEFAULT_AUTHENTICATION_CLASSES': (
                'rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication',
            )
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            warn_if_revocation_is_not_enforced(rest_framework_settings)
        self.assertEqual(len(caught), 1)
        self.assertIn('not checked against the refresh token whitelist', str(caught[0].message))

    def test_no_warning_when_jwt_allauth_class_is_configured(self):
        rest_framework_settings = {
            'DEFAULT_AUTHENTICATION_CLASSES': ('jwt_allauth.authentication.JWTAllAuthAuthentication',)
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            warn_if_revocation_is_not_enforced(rest_framework_settings)
        self.assertEqual(len(caught), 0)

    @override_settings(JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK=False)
    def test_no_warning_when_the_check_is_disabled(self):
        rest_framework_settings = {
            'DEFAULT_AUTHENTICATION_CLASSES': (
                'rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication',
            )
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            warn_if_revocation_is_not_enforced(rest_framework_settings)
        self.assertEqual(len(caught), 0)

    def test_no_warning_for_a_custom_authentication_class(self):
        rest_framework_settings = {
            'DEFAULT_AUTHENTICATION_CLASSES': ('myproject.auth.MyAuthentication',)
        }
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            warn_if_revocation_is_not_enforced(rest_framework_settings)
        self.assertEqual(len(caught), 0)
