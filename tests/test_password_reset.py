import hashlib
import re
import time
from datetime import timedelta
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from jwt_allauth.constants import (
    PASS_RESET, PASS_RESET_ACCESS, PASS_RESET_COOKIE, FOR_USER, ONE_TIME_PERMISSION,
    REFRESH_TOKEN_COOKIE
)
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.tokens.tokens import GenericToken
from jwt_allauth.utils import load_capability_user
from .mixins import APIClient, TestsMixin


class PasswordResetTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_password_reset(self):
        mail_count = len(mail.outbox)
        payload = {'email': self.EMAIL}
        self.post(self.password_reset_url, data=payload, status_code=200)
        self.assertEqual(len(mail.outbox), mail_count + 1)

    def test_password_reset_with_email_in_different_case(self):
        mail_count = len(mail.outbox)
        payload = {'email': self.EMAIL.upper()}
        self.post(self.password_reset_url, data=payload, status_code=200)
        self.assertEqual(len(mail.outbox), mail_count + 1)

    def test_password_reset_with_invalid_email(self):
        """
        Invalid email should not raise error, as this would leak users
        """
        mail_count = len(mail.outbox)
        payload = {'email': 'nonexisting@email.com'}
        self.post(self.password_reset_url, data=payload, status_code=200)
        self.assertEqual(len(mail.outbox), mail_count)

    def test_password_reset_with_empty_email(self):
        payload = {'email': ''}
        resp = self.post(self.password_reset_url, data=payload, status_code=400)
        self.assertEqual(resp['email'][0], u'This field may not be blank.')

    def test_password_reset_empty_payload(self):
        payload = {}
        resp = self.post(self.password_reset_url, data=payload, status_code=400)
        self.assertEqual(resp['email'][0], u'This field is required.')

    def test_password_reset_methods_not_allowed(self):
        resp = self.get(self.password_reset_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "GET" not allowed.')
        resp = self.put(self.password_reset_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.patch(self.password_reset_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PATCH" not allowed.')
        resp = self.delete(self.password_reset_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')

    def test_reset_password(self):
        self.assertEqual(GenericTokenModel.objects.count(), 0)
        self.post(self.password_reset_url, data={'email': self.EMAIL})
        self.assertEqual(GenericTokenModel.objects.count(), 1)
        self.assertEqual(GenericTokenModel.objects.first().purpose, PASS_RESET)
        url = re.findall(r'(https?:\/\/.+)\s+', mail.outbox[-1].body)[0].replace('http://', '')
        url = '/' + '/'.join(url.split('/')[1:])
        hashed_token = GenericTokenModel.objects.first().token
        self.assertEqual(hashlib.sha256(str(url.split('/')[-2]).encode()).hexdigest(), hashed_token)
        resp = self.get(url, status_code=302)
        self.assertIn(PASS_RESET_COOKIE, resp.cookies)

        access_token_str = resp.cookies[PASS_RESET_COOKIE].value
        access_token = self.TOKEN.access_token_class(access_token_str)
        self.assertIn(FOR_USER, access_token)
        self.assertEqual(access_token[FOR_USER], self.USER.id)
        self.assertIn(ONE_TIME_PERMISSION, access_token)
        self.assertEqual(access_token[ONE_TIME_PERMISSION], PASS_RESET_ACCESS)
        self.client.cookies.load({PASS_RESET_COOKIE: access_token_str})
        new_password = 'NewPassw0rdP@swordReset'
        resp = self.client.post(
            reverse("rest_password_reset_set_new"),
            data={'new_password1': new_password, 'new_password2': new_password},
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

        payload = {
            "email": self.EMAIL,
            "password": new_password
        }
        self.post(self.login_url, data=payload, status_code=200)

    def test_reset_with_invalid_token(self):
        invalid_url = '/password/reset/confirm/invalid-token/'
        self.get(invalid_url, status_code=404)

    def test_email_normalization(self):
        self.post(self.password_reset_url, data={'email': self.EMAIL.upper() + ' '})
        self.assertEqual(GenericTokenModel.objects.count(), 1)
        token = GenericTokenModel.objects.first()
        self.assertEqual(token.user.email, self.EMAIL)

    # @transaction.non_atomic_requests
    def test_concurrent_reset_requests(self):
        self.assertEqual(GenericTokenModel.objects.count(), 0)
        self.post(self.password_reset_url, data={'email': self.EMAIL})
        self.assertEqual(GenericTokenModel.objects.count(), 1)
        token1 = GenericTokenModel.objects.first()
        # Sleep 2 seconds, if not, the token is repeated
        time.sleep(2)
        self.post(self.password_reset_url, data={'email': self.EMAIL})
        self.assertEqual(GenericTokenModel.objects.count(), 1)
        token2 = GenericTokenModel.objects.first()
        self.assertNotEqual(token1.token, token2.token)

    def _issue_reset_capability(self):
        """Walk a reset link end to end and return the capability cookie it hands out."""
        token = GenericToken(purpose=PASS_RESET).make_token(self.USER)
        uid = urlsafe_base64_encode(force_bytes(self.USER.pk))
        resp = self.client.get(reverse("password_reset_confirm", args=(uid, token)))
        self.assertEqual(resp.status_code, 302)
        return resp.cookies[PASS_RESET_COOKIE].value

    def test_second_reset_supersedes_the_previous_capability(self):
        """Two reset requests must not leave two capabilities alive at the same time."""
        superseded = self._issue_reset_capability()
        current = self._issue_reset_capability()
        self.assertNotEqual(superseded, current)

        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}

        self.client.cookies.load({PASS_RESET_COOKIE: superseded})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

        self.client.cookies.load({PASS_RESET_COOKIE: current})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

    def test_reset_capability_is_claimed_once(self):
        """Only the caller that removed the row owns the capability."""
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )

        self.assertTrue(GenericTokenModel.consume(access_token["jti"], PASS_RESET_ACCESS))
        self.assertFalse(GenericTokenModel.consume(access_token["jti"], PASS_RESET_ACCESS))

    def test_reset_password_tokens(self):
        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}

        # no token
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

        # invalid token
        self.client.cookies.load({PASS_RESET_COOKIE: "invalid"})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

        # actual token - invalid
        self.client.cookies.load({PASS_RESET_COOKIE: str(self.ACCESS)})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

        # actual token - valid
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )
        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

    @patch("rest_framework_simplejwt.tokens.AccessToken.lifetime", timedelta(microseconds=1))
    def test_set_password_expired_token(self):
        token = GenericToken(purpose=PASS_RESET).make_token(self.USER)
        uid = urlsafe_base64_encode(force_bytes(self.USER.pk))

        resp = self.client.get(reverse("password_reset_confirm", args=(uid, token)))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(PASS_RESET_COOKIE, resp.cookies)
        # token expired
        time.sleep(0.001)
        # check the token is correct
        with self.assertRaises(TokenError):
            self.TOKEN.access_token_class(
                resp.cookies[PASS_RESET_COOKIE].value
            )

        # test reset password API
        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        self.client.cookies.load({PASS_RESET_COOKIE: resp.cookies[PASS_RESET_COOKIE].value})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

    def test_set_password_view_methods(self):
        """Test that SetPasswordView only allows POST method."""
        # Create valid token for testing
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )

        # Setup token in cookies
        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})

        # POST should be implemented
        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertNotEqual(resp.status_code, 405)

        # Recreate token as it was consumed
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )

        # All other methods should return 405 Method Not Allowed
        resp = self.client.get(reverse("rest_password_reset_set_new"))
        self.assertEqual(resp.status_code, 405)

        resp = self.client.put(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 405)

        resp = self.client.patch(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 405)

        resp = self.client.delete(reverse("rest_password_reset_set_new"))
        self.assertEqual(resp.status_code, 405)

    def test_set_password_token_not_whitelisted(self):
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        # Setup token in cookies
        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})
        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

    def test_set_password_token_reuse(self):
        """Test that set password tokens cannot be reused."""
        # Create valid token
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )

        # Setup token in cookies
        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})

        # First use of token (should work)
        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

        # Second use of token (should fail as token was consumed)
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 401)

    def test_old_password_invalid_after_reset(self):
        old_password = self.PASS
        new_password = 'NewPassw0rdP@swordReset'
        self.post(self.password_reset_url, data={'email': self.EMAIL})
        url = re.findall(r'(https?://\S+)', mail.outbox[-1].body)[0].replace('http://', '')
        url = '/' + '/'.join(url.split('/')[1:])
        resp = self.get(url, status_code=302)
        self.client.cookies.load({PASS_RESET_COOKIE: resp.cookies[PASS_RESET_COOKIE].value})
        self.client.post(
            reverse("rest_password_reset_set_new"),
            data={'new_password1': new_password, 'new_password2': new_password},
            content_type="application/json"
        )
        payload = {"email": self.EMAIL, "password": old_password}
        self.post(self.login_url, data=payload, status_code=401)

    def test_reset_confirm_public_with_restrictive_project_default(self):
        """
        The link sent by email is opened by an anonymous user, so the confirm
        view must stay public even when the project sets a restrictive
        ``DEFAULT_PERMISSION_CLASSES`` (e.g. ``IsAuthenticated``).
        """
        token = GenericToken(purpose=PASS_RESET).make_token(self.USER)
        uid = urlsafe_base64_encode(force_bytes(self.USER.pk))

        # Emulate a project-wide default of IsAuthenticated: views that do not
        # declare their own ``permission_classes`` inherit it from APIView.
        with patch.object(APIView, 'permission_classes', (IsAuthenticated,)):
            resp = self.client.get(reverse("password_reset_confirm", args=(uid, token)))

        self.assertEqual(resp.status_code, 302)
        self.assertIn(PASS_RESET_COOKIE, resp.cookies)

    def test_password_reset_unverified_email(self):
        EmailAddress.objects.filter(user=self.USER).update(verified=False)
        mail_count = len(mail.outbox)
        payload = {'email': self.EMAIL}
        self.post(self.password_reset_url, data=payload, status_code=200)
        self.assertEqual(len(mail.outbox), mail_count)

    def test_password_reset_inactive_user(self):
        self.USER.is_active = False
        self.USER.save()
        mail_count = len(mail.outbox)
        payload = {'email': self.EMAIL}
        self.post(self.password_reset_url, data=payload, status_code=200)
        self.assertEqual(len(mail.outbox), mail_count)

    def test_sessions_revoked(self):
        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()

        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )
        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

        new_session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()
        self.assertTrue(new_session_count < session_count)

    @override_settings(LOGOUT_ON_PASSWORD_CHANGE=False)
    def test_sessions_not_revoked(self):
        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()

        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )
        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})
        resp = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)

        new_session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()
        self.assertTrue(new_session_count >= session_count)

    def test_password_reset_complete_refresh_token_as_cookie_default(self):
        """Test that refresh token is sent as cookie by default after password reset"""
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )

        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})
        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        response = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn('access', response_data)
        self.assertNotIn('refresh', response_data)  # Should not be in JSON response

        # Check that cookie was set
        self.assertIn(REFRESH_TOKEN_COOKIE, response.cookies)
        self.assertTrue(response.cookies[REFRESH_TOKEN_COOKIE]['httponly'])

    @override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False)
    def test_password_reset_complete_refresh_token_in_payload(self):
        """Test that refresh token is sent in payload when configured after password reset"""
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token["jti"], purpose=PASS_RESET_ACCESS, user=self.USER
        )

        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})
        data = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        response = self.client.post(
            reverse("rest_password_reset_set_new"), data=data, content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn('access', response_data)
        self.assertIn('refresh', response_data)  # Should be in JSON response

        # Check that cookie was NOT set
        self.assertNotIn(REFRESH_TOKEN_COOKIE, response.cookies)


class PasswordResetAccountStateTests(TestsMixin):
    """
    The state of the account is re-read when the capability is used.

    A capability is minted once and carries the id of the account it was issued for, so
    nothing about the account it names is checked again unless the endpoint that consumes
    it looks the account up.
    """

    SET_NEW_DATA = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}

    def setUp(self):
        self.init()

    def _capability(self):
        """Hand the client a valid password reset capability."""
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = self.USER.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
        access_token = refresh_token.access_token
        GenericTokenModel.objects.create(
            token=access_token['jti'], purpose=PASS_RESET_ACCESS, user=self.USER
        )
        self.client.cookies.load({PASS_RESET_COOKIE: str(access_token)})
        return access_token

    def _set_new_password(self):
        return self.client.post(
            reverse('rest_password_reset_set_new'),
            data=self.SET_NEW_DATA,
            content_type='application/json',
        )

    def test_reset_rejected_for_deactivated_account(self):
        self._capability()
        get_user_model().objects.filter(pk=self.USER.pk).update(is_active=False)

        resp = self._set_new_password()

        self.assertEqual(resp.status_code, 401)
        # No password change and, above all, no session for a deactivated account.
        self.USER.refresh_from_db()
        self.assertTrue(self.USER.check_password(self.PASS))
        self.assertNotIn(REFRESH_TOKEN_COOKIE, resp.cookies)

    def test_capability_is_spent_by_the_rejected_attempt(self):
        """The capability does not survive the account being deactivated."""
        self._capability()
        get_user_model().objects.filter(pk=self.USER.pk).update(is_active=False)
        self._set_new_password()

        get_user_model().objects.filter(pk=self.USER.pk).update(is_active=True)
        self.assertEqual(self._set_new_password().status_code, 401)
        self.assertFalse(GenericTokenModel.objects.filter(purpose=PASS_RESET_ACCESS).exists())

    def test_confirm_link_issues_no_capability_for_a_deactivated_account(self):
        token = GenericToken(purpose=PASS_RESET).make_token(self.USER)
        uid = urlsafe_base64_encode(force_bytes(self.USER.pk))
        get_user_model().objects.filter(pk=self.USER.pk).update(is_active=False)

        resp = self.client.get(reverse('password_reset_confirm', args=(uid, token)))

        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(PASS_RESET_COOKIE, resp.cookies)
        self.assertFalse(GenericTokenModel.objects.filter(purpose=PASS_RESET_ACCESS).exists())

    def test_capability_user_gone(self):
        """A capability naming an account that no longer exists is rejected, not a 500."""
        user_id = self.USER.id
        self.USER.delete()
        with self.assertRaises(InvalidToken):
            load_capability_user(user_id)

    def test_capability_user_deactivated(self):
        get_user_model().objects.filter(pk=self.USER.pk).update(is_active=False)
        with self.assertRaises(InvalidToken):
            load_capability_user(self.USER.id)


class PasswordResetCSRFTests(TestsMixin):
    """
    The capability travels in a cookie, so the reset endpoint needs a CSRF token.

    Nothing else stands between another origin and the endpoint once the cookie is
    configured with ``SameSite='None'``, which a frontend on a different site requires.
    """

    SET_NEW_DATA = {"new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}

    def setUp(self):
        self.init()
        # The default client skips CSRF entirely; these tests need it enforced.
        self.client = APIClient(enforce_csrf_checks=True)

    def _follow_reset_link(self):
        """Walk the reset flow up to the redirect that hands out the capability."""
        token = GenericToken(purpose=PASS_RESET).make_token(self.USER)
        uid = urlsafe_base64_encode(force_bytes(self.USER.pk))
        return self.client.get(reverse('password_reset_confirm', args=(uid, token)))

    def _set_new_password(self, **extra):
        return self.client.post(
            reverse('rest_password_reset_set_new'),
            data=self.SET_NEW_DATA,
            content_type='application/json',
            **extra,
        )

    def test_capability_redirect_hands_out_a_csrf_cookie(self):
        resp = self._follow_reset_link()

        self.assertEqual(resp.status_code, 302)
        self.assertIn(PASS_RESET_COOKIE, resp.cookies)
        self.assertIn(django_settings.CSRF_COOKIE_NAME, resp.cookies)

    def test_reset_without_csrf_token_is_rejected(self):
        self._follow_reset_link()

        resp = self._set_new_password()

        self.assertEqual(resp.status_code, 403)
        self.USER.refresh_from_db()
        self.assertTrue(self.USER.check_password(self.PASS))
        # The capability is not spent by a request that never got through.
        self.assertTrue(GenericTokenModel.objects.filter(purpose=PASS_RESET_ACCESS).exists())

    def test_reset_with_csrf_token_goes_through(self):
        self._follow_reset_link()
        csrf_token = self.client.cookies[django_settings.CSRF_COOKIE_NAME].value

        resp = self._set_new_password(HTTP_X_CSRFTOKEN=csrf_token)

        self.assertEqual(resp.status_code, 200)
        self.USER.refresh_from_db()
        self.assertTrue(self.USER.check_password(self.SET_NEW_DATA['new_password1']))

    @override_settings(JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF=False)
    def test_check_can_be_turned_off(self):
        self._follow_reset_link()

        resp = self._set_new_password()

        self.assertEqual(resp.status_code, 200)
