"""
Behaviour of ``ACCOUNT_EMAIL_VERIFICATION = 'optional'``.

allauth's ``'optional'`` means *send the confirmation mail, but do not block*. Until the
setting was honoured here it behaved as a ``'mandatory'`` with a different enumeration
story: the mail went out, the sign-up handed back nothing usable and the login refused
the account. These tests pin down the shape it has now -- the account is usable from
sign-up and verification governs features through the ``email_verified`` claim -- and
that the other two values are untouched.
"""

import re

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from unittest.mock import patch

from jwt_allauth.constants import EMAIL_VERIFIED_CLAIM, REFRESH_TOKEN_COOKIE
from jwt_allauth.permissions import BasePermission, IsEmailVerified
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.tokens import RefreshToken

from .mixins import TestsMixin


class RegularUserPermission(BasePermission):
    accepted_roles = [0]


@override_settings(ACCOUNT_EMAIL_VERIFICATION='optional')
class OptionalEmailVerificationTests(TestsMixin):

    REGISTRATION_EMAIL = 'optional_verification@email.com'
    REGISTRATION_DATA = {
        "email": REGISTRATION_EMAIL,
        "password1": TestsMixin.PASS,
        "password2": TestsMixin.PASS,
        "first_name": TestsMixin.FIRST_NAME,
        "last_name": TestsMixin.LAST_NAME,
    }
    REGISTRATION_LOGIN_DATA = {
        "email": REGISTRATION_EMAIL,
        "password": TestsMixin.PASS,
    }

    def setUp(self):
        self.init()

    @staticmethod
    def _mail_body(message):
        return ' '.join([message.body] + [alt for alt, _ in getattr(message, 'alternatives', [])])

    def _verification_key_from_mail(self, message):
        match = re.search(r'/registration/verification/([^/\s"\'<>]+)/', self._mail_body(message))
        self.assertIsNotNone(match)
        return match.group(1)

    def _register(self):
        """
        Sign up and return the response, the session it opened and the confirmation key.

        The refresh token travels in the ``refresh_token`` cookie, as it does everywhere
        else in the library, so it is read from there rather than from the body.
        """
        mail.outbox = []
        resp = self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn('refresh', resp)
        refresh = self.response.cookies[REFRESH_TOKEN_COOKIE].value
        return resp, refresh, self._verification_key_from_mail(mail.outbox[0])

    @staticmethod
    def _claim(access_token):
        return RefreshToken.access_token_class(access_token).payload.get(EMAIL_VERIFIED_CLAIM)

    # -- Sign-up ---------------------------------------------------------------------

    def test_registration_hands_out_a_usable_session(self):
        """
        The confirmation mail is still sent, but the sign-up answers with tokens that
        work: the account is usable from the start.
        """
        resp, refresh, _key = self._register()

        self.assertIn('access', resp)
        self.assertTrue(refresh)

        new_user = get_user_model().objects.latest('id')
        self.assertFalse(EmailAddress.objects.get(user=new_user, email=self.REGISTRATION_EMAIL).verified)
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(user=new_user, enabled=True).exists())

        self.token = resp['access']
        self.get(self.user_url, status_code=200)

    def test_login_of_an_unverified_account_works(self):
        self._register()

        resp = self.post(self.login_url, data=self.REGISTRATION_LOGIN_DATA, status_code=200)
        self.assertIn('access', resp)

    def test_rotation_of_an_unverified_account_works(self):
        resp, refresh, _key = self._register()

        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh
        refreshed = self.post(self.refresh_url, data={}, status_code=200)
        self.assertIn('access', refreshed)

    # -- The claim -------------------------------------------------------------------

    def test_claim_is_false_until_the_address_is_confirmed(self):
        resp, _refresh, _key = self._register()
        self.assertIs(self._claim(resp['access']), False)

    def test_claim_turns_on_after_the_link_and_a_refresh(self):
        """
        No dedicated endpoint: the frontend calls ``/refresh/`` and the next access
        token carries the claim.
        """
        resp, refresh, key = self._register()

        self.get(f'{self.verify_email_url}{key}/', status_code=302)

        # The token the user is holding still says False -- it was minted before.
        self.assertIs(self._claim(resp['access']), False)

        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh
        refreshed = self.post(self.refresh_url, data={}, status_code=200)
        self.assertIs(self._claim(refreshed['access']), True)

    # -- The permission class --------------------------------------------------------

    @patch("jwt_allauth.user_details.views.UserDetailsView.permission_classes", [IsEmailVerified])
    def test_gated_endpoint_follows_the_claim(self):
        resp, refresh, key = self._register()

        self.token = resp['access']
        self.get(self.user_url, status_code=403)

        self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh
        refreshed = self.post(self.refresh_url, data={}, status_code=200)

        self.token = refreshed['access']
        self.get(self.user_url, status_code=200)

    @patch(
        "jwt_allauth.user_details.views.UserDetailsView.permission_classes",
        [RegularUserPermission & IsEmailVerified],
    )
    def test_composes_with_the_role_permissions(self):
        """
        'regular and verified' needs no permission class of its own.
        """
        resp, refresh, key = self._register()

        self.token = resp['access']
        self.get(self.user_url, status_code=403)

        self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh
        refreshed = self.post(self.refresh_url, data={}, status_code=200)

        self.token = refreshed['access']
        self.get(self.user_url, status_code=200)

    @patch("jwt_allauth.user_details.views.UserDetailsView.permission_classes", [IsEmailVerified])
    def test_a_token_without_the_claim_is_denied(self):
        """
        Tokens minted before the claim existed fail closed. Rotating gets it back.
        """
        refresh = RefreshToken.for_user(self.USER)
        del refresh.payload[EMAIL_VERIFIED_CLAIM]

        self.token = str(refresh.access_token)
        self.get(self.user_url, status_code=403)

    # -- The confirmation link --------------------------------------------------------

    def test_the_link_alone_starts_no_session(self):
        _resp, _refresh, key = self._register()

        response = self.client.get(f'{self.verify_email_url}{key}/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, response.cookies)

    @override_settings(JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION=True)
    def test_the_link_starts_a_session_when_asked_to(self):
        _resp, _refresh, key = self._register()

        response = self.client.get(f'{self.verify_email_url}{key}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn(REFRESH_TOKEN_COOKIE, response.cookies)

    # -- Credential changes ------------------------------------------------------------

    def test_password_change_revokes_every_previous_session(self):
        """
        The account changing hands is the whole point: whoever signed up with somebody
        else's address keeps nothing once the owner sets a password.
        """
        resp, refresh, _key = self._register()
        intruder_refresh = refresh

        login = self.post(self.login_url, data=self.REGISTRATION_LOGIN_DATA, status_code=200)
        caller_refresh = self.client.cookies[REFRESH_TOKEN_COOKIE].value

        self.token = login['access']
        changed = self.post(
            self.password_change_url,
            data={
                "old_password": self.PASS,
                "new_password1": "new_pass00",
                "new_password2": "new_pass00",
            },
            status_code=200,
        )
        self.assertIn('access', changed)

        with override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False):
            self.post(self.refresh_url, data={'refresh': intruder_refresh}, status_code=401)
            self.post(self.refresh_url, data={'refresh': caller_refresh}, status_code=401)


class MandatoryVerificationIsUnchangedTests(TestsMixin):
    """
    The values that are not ``'optional'`` keep the behaviour they had. Left explicit
    because the predicate they share now lives in one place.
    """

    def setUp(self):
        self.init()

    def _unverify(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        email_object.verified = False
        email_object.save()
        return email_object

    def test_undeclared_setting_still_blocks_the_login(self):
        self._unverify()
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=401)
        self.assertEqual(resp['code'], u'email_not_verified')

    @override_settings(ACCOUNT_EMAIL_VERIFICATION='mandatory')
    def test_explicit_mandatory_still_blocks_the_login(self):
        self._unverify()
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=401)
        self.assertEqual(resp['code'], u'email_not_verified')

    @override_settings(ACCOUNT_EMAIL_VERIFICATION='none', EMAIL_VERIFICATION=False)
    def test_none_never_blocked_the_login(self):
        self._unverify()
        self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)

    def test_claim_reflects_a_verified_address(self):
        token = RefreshToken.for_user(self.USER)
        self.assertIs(token.payload[EMAIL_VERIFIED_CLAIM], True)

        key = EmailConfirmationHMAC(self._unverify()).key
        self.assertIs(RefreshToken.for_user(self.USER).payload[EMAIL_VERIFIED_CLAIM], False)

        self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertIs(RefreshToken.for_user(self.USER).payload[EMAIL_VERIFIED_CLAIM], True)
