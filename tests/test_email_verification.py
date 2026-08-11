import time

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.test import override_settings
from django.urls import reverse

from jwt_allauth.constants import REFRESH_TOKEN_COOKIE

from .mixins import TestsMixin


class EmailVerificationTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_email_verification_no_key(self):
        self.get(self.verify_email_url, status_code=404)

    def test_email_verification_with_invalid_key(self):
        self.get(self.verify_email_url + 'fakeKey/', status_code=404)

    def test_email_verification(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        email_object.verified = False
        email_object.save()

        key = EmailConfirmationHMAC(email_object).key

        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=401)
        self.assertEqual(resp['code'], u'email_not_verified')

        self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertTrue(EmailAddress.objects.get(user=self.USER, email=self.EMAIL).verified)

        self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)

    def test_email_verification_email_already_verified(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        self.assertTrue(email_object.verified)

        key = EmailConfirmationHMAC(email_object).key

        self.get(f'{self.verify_email_url}{key}/', status_code=404)

    @override_settings(ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=0.000000000001)
    def test_email_verification_expired_key(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        email_object.verified = False
        email_object.save()

        confirmation = EmailConfirmationHMAC(email_object)
        key = confirmation.key
        time.sleep(.1)

        self.get(f'{self.verify_email_url}{key}/', status_code=404)
        self.assertFalse(EmailAddress.objects.get(user=self.USER, email=self.EMAIL).verified)

    def test_email_verification_deleted_email(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        key = EmailConfirmationHMAC(email_object).key
        email_object.delete()

        self.get(f'{self.verify_email_url}{key}/', status_code=404)

    def test_email_verification_redirect_url(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        email_object.verified = False
        email_object.save()

        key = EmailConfirmationHMAC(email_object).key

        resp = self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertRedirects(resp, expected_url='/jwt-allauth/registration/verified/', fetch_redirect_response=False)

    @override_settings(EMAIL_VERIFIED_REDIRECT="/test-verified/")
    def test_email_verification_redirect_url_modified(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        email_object.verified = False
        email_object.save()

        key = EmailConfirmationHMAC(email_object).key

        resp = self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertRedirects(resp, expected_url='/test-verified/', fetch_redirect_response=False)

    def _unverify(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        email_object.verified = False
        email_object.save()
        return email_object

    def test_email_verification_starts_no_session_by_default(self):
        key = EmailConfirmationHMAC(self._unverify()).key

        resp = self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, resp.cookies)

    @override_settings(JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION=True)
    def test_email_verification_starts_a_session(self):
        """
        The browser that follows the link ends up with a usable session, which is what
        registration itself can no longer hand out.
        """
        key = EmailConfirmationHMAC(self._unverify()).key

        resp = self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertIn(REFRESH_TOKEN_COOKIE, resp.cookies)
        self.assertTrue(resp.cookies[REFRESH_TOKEN_COOKIE]['httponly'])

        self.client.cookies[REFRESH_TOKEN_COOKIE] = resp.cookies[REFRESH_TOKEN_COOKIE].value
        refreshed = self.post(reverse('token_refresh'), data={}, status_code=200)
        self.assertIn('access', refreshed)

    @override_settings(
        JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION=True,
        JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False,
    )
    def test_email_verification_starts_no_session_without_cookies(self):
        """
        A redirect has nowhere to put a token when the installation does not use
        cookies, and the URL is not an acceptable place for one.
        """
        key = EmailConfirmationHMAC(self._unverify()).key

        resp = self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, resp.cookies)

    @override_settings(JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION=True)
    def test_secondary_address_verification_starts_no_session(self):
        """
        Confirming an address added to an account that is already usable verifies the
        address, nothing more.
        """
        secondary = EmailAddress.objects.create(user=self.USER, email='secondary@email.com', verified=False)
        key = EmailConfirmationHMAC(secondary).key

        resp = self.get(f'{self.verify_email_url}{key}/', status_code=302)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, resp.cookies)
        secondary.refresh_from_db()
        self.assertTrue(secondary.verified)

    def test_email_verification_not_allowed_methods(self):
        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        email_object.verified = False
        email_object.save()

        key = EmailConfirmationHMAC(email_object).key

        self.post(f'{self.verify_email_url}{key}/', status_code=405)
        resp = self.put(f'{self.verify_email_url}{key}/', status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.patch(f'{self.verify_email_url}{key}/', status_code=405)
        self.assertEqual(resp['detail'], u'Method "PATCH" not allowed.')
        resp = self.delete(f'{self.verify_email_url}{key}/', status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')
