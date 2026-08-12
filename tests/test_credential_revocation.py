"""
What a credential change takes down with it, and the notice that tells the owner of an
address to trigger one.

Both belong to the same story. Under ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` an
account is usable before its address is confirmed, so somebody can sign up with an
address that is not theirs and hold a session on it. The owner's way out is the password
reset -- which only works if it takes *everything* -- and the only thing that tells them
to use it is the 'account already exists' mail.
"""

import re

from allauth.account.models import EmailAddress
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from jwt_allauth.constants import PASS_RESET, PASS_RESET_COOKIE, REFRESH_TOKEN_COOKIE
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.tokens.tokens import GenericToken, RefreshToken

from .mixins import TestsMixin


class CredentialChangeRevocationTests(TestsMixin):

    def setUp(self):
        self.init()

    def _reset_capability(self):
        token = GenericToken(purpose=PASS_RESET).make_token(self.USER)
        uid = urlsafe_base64_encode(force_bytes(self.USER.pk))
        resp = self.client.get(reverse("password_reset_confirm", args=(uid, token)))
        self.assertEqual(resp.status_code, 302)
        return resp.cookies[PASS_RESET_COOKIE].value

    def _set_new_password(self, capability, password='P@sw0rd-set'):
        self.client.cookies.load({PASS_RESET_COOKIE: capability})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"),
            data={'new_password1': password, 'new_password2': password},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        return resp

    def test_reset_leaves_no_session_alive(self):
        RefreshToken.for_user(self.USER)
        RefreshToken.for_user(self.USER)
        capability = self._reset_capability()

        self._set_new_password(capability)

        # Only the session the reset itself handed out survives.
        self.assertEqual(RefreshTokenWhitelistModel.objects.filter(user=self.USER).count(), 1)

    def test_reset_leaves_no_pending_capability_alive(self):
        """
        A second reset link that was requested but never followed is a way back in for
        whoever requested it, so it does not outlive the handover.
        """
        pending = GenericToken(purpose=PASS_RESET).make_token(self.USER)
        capability = self._reset_capability()

        self._set_new_password(capability)

        self.assertFalse(GenericTokenModel.objects.filter(user=self.USER).exists())
        uid = urlsafe_base64_encode(force_bytes(self.USER.pk))
        resp = self.client.get(reverse("password_reset_confirm", args=(uid, pending)))
        self.assertEqual(resp.status_code, 200)  # the 'invalid link' page, not a redirect
        self.assertNotIn(PASS_RESET_COOKIE, resp.cookies)

    def test_reset_cancels_an_address_change_in_flight(self):
        """
        An unconfirmed address queued up behind the primary one would let whoever added
        it take the account over later, so it goes with the rest.
        """
        EmailAddress.objects.create(user=self.USER, email='in-flight@email.com', verified=False)
        capability = self._reset_capability()

        self._set_new_password(capability)

        self.assertFalse(EmailAddress.objects.filter(user=self.USER, verified=False).exists())
        # The account's own address is untouched.
        self.assertTrue(EmailAddress.objects.filter(user=self.USER, email=self.EMAIL).exists())

    def test_reset_keeps_an_unconfirmed_primary_address(self):
        """
        Under mandatory verification the primary address is unconfirmed until the link
        is followed; dropping it would leave the account with no address at all.
        """
        primary = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        primary.verified = False
        primary.save()

        self._set_new_password(self._reset_capability())

        self.assertTrue(EmailAddress.objects.filter(user=self.USER, email=self.EMAIL).exists())

    def test_password_change_cancels_an_address_change_in_flight(self):
        EmailAddress.objects.create(user=self.USER, email='in-flight@email.com', verified=False)

        self.token = self.ACCESS
        self.post(
            self.password_change_url,
            data={
                "old_password": self.PASS,
                "new_password1": "P@sw0rd-set",
                "new_password2": "P@sw0rd-set",
            },
            status_code=200,
        )

        self.assertFalse(EmailAddress.objects.filter(user=self.USER, verified=False).exists())

    @override_settings(LOGOUT_ON_PASSWORD_CHANGE=False)
    def test_opting_out_revokes_nothing(self):
        EmailAddress.objects.create(user=self.USER, email='in-flight@email.com', verified=False)
        RefreshToken.for_user(self.USER)
        sessions = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()

        self.token = self.ACCESS
        resp = self.post(
            self.password_change_url,
            data={
                "old_password": self.PASS,
                "new_password1": "P@sw0rd-set",
                "new_password2": "P@sw0rd-set",
            },
            status_code=200,
        )

        # No revocation, and therefore no replacement session in the response either.
        self.assertNotIn('access', resp)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, self.response.cookies)
        self.assertEqual(RefreshTokenWhitelistModel.objects.filter(user=self.USER).count(), sessions)
        self.assertTrue(EmailAddress.objects.filter(user=self.USER, verified=False).exists())


class AccountAlreadyExistsNoticeTests(TestsMixin):
    """
    The notice is the only warning the owner of an address gets when somebody signs up
    with it, so it has to say how to take the account back.
    """

    REGISTRATION_DATA = {
        "email": TestsMixin.EMAIL,
        "password1": TestsMixin.PASS,
        "password2": TestsMixin.PASS,
        "first_name": TestsMixin.FIRST_NAME,
        "last_name": TestsMixin.LAST_NAME,
    }

    def setUp(self):
        self.init()

    def _notice(self):
        mail.outbox = []
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.EMAIL])
        return ' '.join([message.body] + [alt for alt, _ in getattr(message, 'alternatives', [])])

    def test_notice_tells_the_owner_to_take_the_account_back(self):
        body = self._notice()

        self.assertIn('If it was not you and this address is yours', body)
        self.assertIn('Reset the password to take control of the account', body)

    @override_settings(PASSWORD_RESET_REQUEST_URL='/forgot-password/')
    def test_notice_links_to_the_reset_form_when_configured(self):
        body = self._notice()

        self.assertIsNotNone(re.search(r'https?://[^"\s]+/forgot-password/', body))

    def test_notice_holds_no_link_without_the_setting(self):
        """
        The library serves no page that asks for a reset, so it links to none until the
        project says where its own is. The instruction is there either way.
        """
        body = self._notice()

        self.assertIn('Reset the password to take control of the account', body)
        self.assertNotIn('forgot-password', body)
