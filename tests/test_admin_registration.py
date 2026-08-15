import re
from datetime import timedelta

from allauth.account import app_settings as allauth_app_settings
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.conf import settings as django_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import NoReverseMatch, clear_url_caches, reverse
from django.utils import timezone
from rest_framework import status

from jwt_allauth.constants import (
    INVITATION,
    SET_PASSWORD_COOKIE,
    PASS_SET_ACCESS,
    REFRESH_TOKEN_COOKIE,
    EMAIL_CONFIRMATION,
)
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.utils import hash_token
from .mixins import APIClient, TestsMixin


@override_settings(
    JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION=True,
    EMAIL_VERIFICATION=True,
    PASSWORD_SET_REDIRECT='/set-password-ui/',
    ROOT_URLCONF='tests.django_urls')
class AdminManagedRegistrationTests(TestsMixin):
    """
    Tests for admin-managed registration flow.
    """

    INVITED_EMAIL = 'invited@demo.com'

    def setUp(self):
        # Clear URL caches to force Django to reload URLs with the new settings
        clear_url_caches()
        from importlib import reload
        import jwt_allauth.registration.urls
        import jwt_allauth.urls
        import tests.django_urls
        reload(jwt_allauth.registration.urls)
        reload(jwt_allauth.urls)
        reload(tests.django_urls)

        self.init()
        self.user_register_url = reverse('rest_user_register')
        self.set_password_url = reverse('rest_set_password')

    def test_default_register_endpoint_not_accessible(self):
        # When admin-managed registration is enabled, /registration/ root should be 404
        response = self.client.post(
            '/registration/', data={"email": self.INVITED_EMAIL}, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # And reversing the original name should fail
        with self.assertRaises(NoReverseMatch):
            reverse('rest_register')

    def test_user_register_requires_allowed_role_by_default(self):
        # Non-staff/non-superuser cannot register others by default
        self.token = self.ACCESS  # auth as default regular user
        payload = {"email": self.INVITED_EMAIL, "role": 300}
        self.post(self.user_register_url, data=payload, status_code=status.HTTP_403_FORBIDDEN)

        # Staff can register users by default
        self.token = self.ACCESS  # auth as default user -> reset
        self._logout()
        staff = get_user_model().objects.create_user(
            'admin1', email='admin1@demo.com', password='A-1_strong', is_staff=True)
        EmailAddress.objects.create(user=staff, email=staff.email, verified=True, primary=True)
        staff_access = str(RefreshToken.for_user(staff).access_token)
        resp = self.client.post(
            self.user_register_url,
            data={"email": self.INVITED_EMAIL, "role": 300},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {staff_access}'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertJSONEqual(resp.content, {})

    @override_settings(JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES=[0])
    def test_custom_allowed_roles_can_register_even_if_not_staff(self):
        # Regular user role 0 is allowed by settings override
        regular = get_user_model().objects.get(email=self.EMAIL)  # created by TestsMixin.init()
        EmailAddress.objects.filter(user=regular).update(verified=True)
        regular_access = str(RefreshToken.for_user(regular).access_token)

        resp = self.client.post(
            self.user_register_url,
            data={"email": self.INVITED_EMAIL, "role": 300},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {regular_access}'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertJSONEqual(resp.content, {})

    @override_settings(JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES=[0])
    def test_staff_not_allowed_when_excluded_by_settings(self):
        staff = get_user_model().objects.create_user(
            'admin3', email='admin3@demo.com', password='A-1_strong', is_staff=True)
        EmailAddress.objects.create(user=staff, email=staff.email, verified=True, primary=True)
        staff_access = str(RefreshToken.for_user(staff).access_token)

        resp = self.client.post(
            self.user_register_url,
            data={"email": self.INVITED_EMAIL, "role": 300},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {staff_access}'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_email_rules(self):
        staff = get_user_model().objects.create_user(
            'admin2', email='admin2@demo.com', password='A-1_strong', is_staff=True)
        EmailAddress.objects.create(user=staff, email=staff.email, verified=True, primary=True)
        staff_access = str(RefreshToken.for_user(staff).access_token)

        # Case 1: existing verified email -> 400
        resp = self.client.post(
            self.user_register_url,
            data={"email": self.EMAIL, "role": 300},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {staff_access}'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resp.json())

        # Case 2: existing unverified email -> allowed, EmailAddress reassigned
        EmailAddress.objects.filter(email=self.EMAIL).update(verified=False)
        resp2 = self.client.post(
            self.user_register_url,
            data={"email": self.EMAIL, "role": 300},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {staff_access}'
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertJSONEqual(resp2.content, {})
        self.assertEqual(EmailAddress.objects.filter(email=self.EMAIL).count(), 1)

    def test_email_confirmation_token_created_on_registration(self):
        """
        When a staff user registers an invited user, a confirmation token should be
        persisted for INVITATION as the digest of the key sent by email — the raw key
        must never be readable from the database.
        """
        staff = get_user_model().objects.create_user(
            'admin_token', email='admin_token@demo.com', password='A-1_strong', is_staff=True
        )
        EmailAddress.objects.create(user=staff, email=staff.email, verified=True, primary=True)
        staff_access = str(RefreshToken.for_user(staff).access_token)

        mail.outbox = []
        resp = self.client.post(
            self.user_register_url,
            data={"email": self.INVITED_EMAIL, "role": 300},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {staff_access}',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        invited = get_user_model().objects.filter(email=self.INVITED_EMAIL).latest('id')
        email_addr = EmailAddress.objects.filter(user=invited, email=self.INVITED_EMAIL).first()
        self.assertIsNotNone(email_addr)

        # Recover the key the invited user actually received
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        body = ' '.join(
            [message.body] + [alt for alt, _ in getattr(message, 'alternatives', [])]
        )
        match = re.search(r'/registration/verification/([^/\s"\'<>]+)/', body)
        self.assertIsNotNone(match)
        key = match.group(1)

        confirmation = EmailConfirmationHMAC.from_key(key)
        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation.email_address, email_addr)

        token = GenericTokenModel.objects.filter(
            user=invited, purpose=INVITATION
        ).first()
        self.assertIsNotNone(token)
        self.assertEqual(token.token, hash_token(key))
        self.assertNotEqual(token.token, key)

    def test_legacy_plain_text_confirmation_token_still_accepted(self):
        """
        Confirmations issued before keys were hashed are stored in plain text; they must
        keep working until they expire.
        """
        invited = get_user_model().objects.create_user('invited_legacy', email=self.INVITED_EMAIL)
        email_addr = EmailAddress.objects.create(
            user=invited, email=self.INVITED_EMAIL, verified=False, primary=True
        )

        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=invited, token=key, purpose=EMAIL_CONFIRMATION)

        resp = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(resp.status_code, 302)
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)

    def test_email_confirmation_token_multi_use_until_password_set(self):
        """
        The INVITATION token allows multiple GET requests (e.g. link scanners).
        It should only be invalidated after the password is set.
        """
        invited = get_user_model().objects.create_user('invited_multi_use', email=self.INVITED_EMAIL)
        email_addr = EmailAddress.objects.create(
            user=invited, email=self.INVITED_EMAIL, verified=False, primary=True
        )

        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=invited, token=hash_token(key), purpose=INVITATION)

        verify_url = reverse('account_confirm_email', args=[key])

        # First use: token is valid and should NOT be consumed
        first_resp = self.client.get(verify_url)
        self.assertEqual(first_resp.status_code, 302)
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertTrue(
            GenericTokenModel.objects.filter(
                user=invited, token=hash_token(key), purpose=INVITATION
            ).exists()
        )

        # Second use: token is still valid
        second_resp = self.client.get(verify_url)
        self.assertEqual(second_resp.status_code, 302)

        # Now set the password
        self.client.post(
            self.set_password_url,
            data={"new_password1": "A-1_newpass", "new_password2": "A-1_newpass"},
            content_type='application/json'
        )

        # Now the token should be gone
        self.assertFalse(
            GenericTokenModel.objects.filter(
                user=invited, token=hash_token(key), purpose=INVITATION
            ).exists()
        )

    def test_email_confirmation_invalid_token_renders_error_page(self):
        """
        If the token is invalid or does not exist, show a friendly error page
        instead of a raw 401/404 or JSON error.
        """
        invalid_url = reverse('account_confirm_email', args=['invalid-key'])
        resp = self.client.get(invalid_url)
        self.assertEqual(resp.status_code, 400)
        self.assertTemplateUsed(resp, 'registration/verification_failed.html')

    def test_email_confirmation_expired_token_renders_error_page(self):
        """
        If the token is expired according to allauth settings, show the error page.
        """
        invited = get_user_model().objects.create_user('invited_expired', email='expired@demo.com')
        email_addr = EmailAddress.objects.create(
            user=invited, email='expired@demo.com', verified=False, primary=True
        )

        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=invited, token=hash_token(key), purpose=INVITATION)

        # Simulate expiration by overriding the setting to 0 days (or -1 if possible, but 0 usually means
        # immediate expiration)
        # However, HMAC is stateless, it embeds timestamp. We need to create a key in the past or fast forward time.
        # Since we can't easily mock time for HMAC generation without patching django-allauth internal,
        # we'll try setting ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS to 0.

        with override_settings(ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=0):
            verify_url = reverse('account_confirm_email', args=[key])
            resp = self.client.get(verify_url)
            self.assertEqual(resp.status_code, 400)
            self.assertTemplateUsed(resp, 'registration/verification_failed.html')

    def test_expired_confirmation_of_verified_user_grants_nothing(self):
        """
        An expired confirmation link must not hand out a password-set capability, not even
        when the account already owns a verified email address (which is what the
        "already verified" fallback used to accept as proof).
        """
        established = get_user_model().objects.create_user(
            'established_expired', email='established_expired@demo.com', password='A-1_strong'
        )
        EmailAddress.objects.create(
            user=established, email='established_expired@demo.com', verified=True, primary=True
        )
        secondary = EmailAddress.objects.create(
            user=established, email='established_expired_work@demo.com', verified=False, primary=False
        )

        key = EmailConfirmationHMAC(secondary).key
        GenericTokenModel.objects.create(user=established, token=hash_token(key), purpose=EMAIL_CONFIRMATION)

        with override_settings(ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=0):
            resp = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(resp.status_code, 400)
        self.assertTemplateUsed(resp, 'registration/verification_failed.html')
        self.assertNotIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertFalse(
            GenericTokenModel.objects.filter(user=established, purpose=PASS_SET_ACCESS).exists()
        )

    def test_confirmation_of_user_with_password_grants_no_capability(self):
        """
        Even with a perfectly valid confirmation key, an account that already has a
        password must never be handed a password-set capability: that would be a password
        reset outside of the reset flow. The address it was sent to is still confirmed.
        """
        established = get_user_model().objects.create_user(
            'established_valid', email='established_valid@demo.com', password='A-1_strong'
        )
        EmailAddress.objects.create(
            user=established, email='established_valid@demo.com', verified=True, primary=True
        )
        secondary = EmailAddress.objects.create(
            user=established, email='established_valid_work@demo.com', verified=False, primary=False
        )

        key = EmailConfirmationHMAC(secondary).key
        GenericTokenModel.objects.create(user=established, token=hash_token(key), purpose=EMAIL_CONFIRMATION)

        resp = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('jwt_allauth_email_verified'))
        self.assertNotIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertFalse(
            GenericTokenModel.objects.filter(user=established, purpose=PASS_SET_ACCESS).exists()
        )
        secondary.refresh_from_db()
        self.assertTrue(secondary.verified)

    def test_pending_account_with_password_is_verified_by_its_link(self):
        """
        A sign-up that chose a password before the installation moved to admin-managed
        registration is not walled off: its link confirms the address, so the account can
        log in with the password it already has. No capability is handed out.
        """
        pending = get_user_model().objects.create_user(
            'pending_with_password', email='pending_with_password@demo.com', password='A-1_strong'
        )
        email_addr = EmailAddress.objects.create(
            user=pending, email='pending_with_password@demo.com', verified=False, primary=True
        )

        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=pending, token=hash_token(key), purpose=EMAIL_CONFIRMATION)

        resp = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('jwt_allauth_email_verified'))
        self.assertNotIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertFalse(
            GenericTokenModel.objects.filter(user=pending, purpose=PASS_SET_ACCESS).exists()
        )
        email_addr.refresh_from_db()
        self.assertTrue(email_addr.verified)

    @override_settings(EMAIL_VERIFIED_REDIRECT='/verified-ui/')
    def test_confirmation_without_capability_honours_the_configured_redirect(self):
        """The built-in page is only routed when the project configured none of its own."""
        established = get_user_model().objects.create_user(
            'established_redirect', email='established_redirect@demo.com', password='A-1_strong'
        )
        email_addr = EmailAddress.objects.create(
            user=established, email='established_redirect@demo.com', verified=False, primary=True
        )

        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=established, token=hash_token(key), purpose=EMAIL_CONFIRMATION)

        resp = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/verified-ui/')

    def test_only_latest_password_set_capability_stays_valid(self):
        """
        Multi-use is allowed until the password is set, but each click supersedes the
        capability granted by the previous one.
        """
        invited = get_user_model().objects.create_user('invited_latest', email=self.INVITED_EMAIL)
        email_addr = EmailAddress.objects.create(
            user=invited, email=self.INVITED_EMAIL, verified=False, primary=True
        )

        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=invited, token=hash_token(key), purpose=INVITATION)
        verify_url = reverse('account_confirm_email', args=[key])

        self.client.get(verify_url)
        first_capability = self.client.cookies[SET_PASSWORD_COOKIE].value

        self.client.get(verify_url)
        second_capability = self.client.cookies[SET_PASSWORD_COOKIE].value

        self.assertNotEqual(first_capability, second_capability)
        self.assertEqual(
            GenericTokenModel.objects.filter(user=invited, purpose=PASS_SET_ACCESS).count(), 1
        )

    def _invite(self, username, email=None, **user_kwargs):
        """Create an invited account and the confirmation it received."""
        email = email or self.INVITED_EMAIL
        invited = get_user_model().objects.create_user(username, email=email, **user_kwargs)
        email_addr = EmailAddress.objects.create(
            user=invited, email=email, verified=False, primary=True
        )
        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=invited, token=hash_token(key), purpose=INVITATION)
        return invited, key

    def test_confirmation_of_deactivated_account_grants_nothing(self):
        """
        A deactivated account gets no password-set capability: login and refresh both
        refuse it, and setting the password opens a session.
        """
        invited, key = self._invite('invited_deactivated', is_active=False)

        resp = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(resp.status_code, 400)
        self.assertTemplateUsed(resp, 'registration/verification_failed.html')
        self.assertNotIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertFalse(
            GenericTokenModel.objects.filter(user=invited, purpose=PASS_SET_ACCESS).exists()
        )

    def test_set_password_rejected_for_deactivated_account(self):
        """A capability issued before the deactivation is not honoured after it."""
        invited, key = self._invite('invited_then_deactivated')
        self.client.get(reverse('account_confirm_email', args=[key]))
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)

        get_user_model().objects.filter(pk=invited.pk).update(is_active=False)

        resp = self.client.post(
            self.set_password_url,
            data={"new_password1": "A-1_newpass", "new_password2": "A-1_newpass"},
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn(REFRESH_TOKEN_COOKIE, resp.cookies)
        invited.refresh_from_db()
        self.assertFalse(invited.has_usable_password())

    def test_set_password_completes_with_an_authorization_header_attached(self):
        """
        Authorization here is the one-time cookie, and the permission behind it turns down
        a request that arrives already authenticated. A native client attaching its bearer
        token to every request must still be able to finish the invitation.
        """
        invited, key = self._invite('invited_with_bearer')
        staff = get_user_model().objects.create_user(
            'bearer_staff', email='bearer_staff@demo.com', password='A-1_strong', is_staff=True
        )
        EmailAddress.objects.create(user=staff, email=staff.email, verified=True, primary=True)
        bearer = 'Bearer %s' % RefreshToken.for_user(staff).access_token

        verify_resp = self.client.get(
            reverse('account_confirm_email', args=[key]), HTTP_AUTHORIZATION=bearer
        )
        self.assertEqual(verify_resp.status_code, 302)
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)

        resp = self.client.post(
            self.set_password_url,
            data={"new_password1": "A-1_newpass", "new_password2": "A-1_newpass"},
            content_type='application/json',
            HTTP_AUTHORIZATION=bearer,
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        invited.refresh_from_db()
        self.assertTrue(invited.has_usable_password())

    def test_set_password_requires_a_csrf_token(self):
        """
        The capability travels in a cookie, so the endpoint that consumes it has to
        check the CSRF token — the ``SameSite`` policy of the cookie is a deployment
        setting, not a guarantee.
        """
        csrf_client = APIClient(enforce_csrf_checks=True)
        _, key = self._invite('invited_csrf')
        verify_resp = csrf_client.get(reverse('account_confirm_email', args=[key]))
        self.assertIn(SET_PASSWORD_COOKIE, verify_resp.cookies)
        # The redirect carries the token the frontend has to send back.
        self.assertIn(django_settings.CSRF_COOKIE_NAME, verify_resp.cookies)

        data = {"new_password1": "A-1_newpass", "new_password2": "A-1_newpass"}
        resp = csrf_client.post(self.set_password_url, data=data, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        resp = csrf_client.post(
            self.set_password_url,
            data=data,
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_client.cookies[django_settings.CSRF_COOKIE_NAME].value,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_set_password_flow(self):
        """
        Simulate the verification GET that issues a one-time access token cookie,
        then set the password and verify login works.
        """
        invited = get_user_model().objects.create_user('invited', email=self.INVITED_EMAIL)
        email_addr = EmailAddress.objects.create(
            user=invited, email=self.INVITED_EMAIL, verified=False, primary=True)

        # Simulate clicking the verification link sent by email
        key = EmailConfirmationHMAC(email_addr).key
        # Persist confirmation token as it would be created by the adapter
        GenericTokenModel.objects.create(user=invited, token=hash_token(key), purpose=INVITATION)
        verify_url = reverse('account_confirm_email', args=[key])
        verify_resp = self.client.get(verify_url)
        self.assertEqual(verify_resp.status_code, 302)  # redirected after confirming
        # One-time token cookie must be present
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)
        # Token persisted server-side for single use
        self.assertTrue(GenericTokenModel.objects.filter(user=invited, purpose=PASS_SET_ACCESS).exists())

        # Use client.post directly to access response.cookies
        response = self.client.post(
            self.set_password_url,
            data={"new_password1": "A-1_newpass", "new_password2": "A-1_newpass"},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.json())

        # If refresh is cookie-based by default, ensure cookie was set
        self.assertIn(REFRESH_TOKEN_COOKIE, response.cookies)
        self.assertTrue(response.cookies[REFRESH_TOKEN_COOKIE]['httponly'])

        # And the invited user can now log in using the new password
        login_response = self.client.post(
            self.login_url,
            data={"email": self.INVITED_EMAIL, "password": "A-1_newpass"},
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.json())


@override_settings(
    JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION=True, EMAIL_VERIFICATION=False, ROOT_URLCONF='tests.django_urls')
class AdminManagedEmailVerificationOffTests(TestsMixin):
    """
    Ensure EMAIL_VERIFICATION=False impacts only the verification route inclusion,
    not the admin-managed endpoints like user-register/set-password.
    """

    INVITED_EMAIL = 'invited_off@demo.com'

    def setUp(self):
        # Clear URL caches to force Django to reload URLs with the new settings
        clear_url_caches()
        from importlib import reload
        import jwt_allauth.registration.urls
        import jwt_allauth.urls
        import tests.django_urls
        reload(jwt_allauth.registration.urls)
        reload(jwt_allauth.urls)
        reload(tests.django_urls)

        self.init()
        self.user_register_url = reverse('rest_user_register')
        self.set_password_url = reverse('rest_set_password')

    def test_verification_route_absent(self):
        with self.assertRaises(NoReverseMatch):
            reverse('account_confirm_email')
        resp = self.client.get('/registration/verification/somekey/', content_type='application/json')
        self.assertEqual(resp.status_code, 404)

    def test_user_register_and_email_unverified(self):
        # Staff registers user; email should be created but remain unverified
        staff = get_user_model().objects.create_user(
            'admin_off', email='admin_off@demo.com', password='A-1_strong', is_staff=True)
        EmailAddress.objects.create(user=staff, email=staff.email, verified=True, primary=True)
        staff_access = str(RefreshToken.for_user(staff).access_token)

        resp = self.client.post(
            self.user_register_url,
            data={"email": self.INVITED_EMAIL, "role": 300},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {staff_access}'
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        invited = get_user_model().objects.filter(email=self.INVITED_EMAIL).latest('id')
        email = EmailAddress.objects.filter(user=invited).first()
        self.assertIsNotNone(email)
        self.assertFalse(email.verified)

    def test_set_password_route_present(self):
        # Route exists even if we cannot reach it without verification cookie
        url = reverse('rest_set_password')
        self.assertTrue(url.endswith('/registration/set-password/'))

    @override_settings(EMAIL_VERIFICATION=True)
    def test_set_password_and_login_flow(self):
        """
        Temporarily enable verification route to simulate the full flow and assert login works.
        """
        # Reload URLs to pick up EMAIL_VERIFICATION=True for this test
        clear_url_caches()
        from importlib import reload
        import jwt_allauth.registration.urls
        import jwt_allauth.urls
        import tests.django_urls
        reload(jwt_allauth.registration.urls)
        reload(jwt_allauth.urls)
        reload(tests.django_urls)

        invited = get_user_model().objects.create_user('invited_off', email=self.INVITED_EMAIL)
        email_addr = EmailAddress.objects.create(user=invited, email=self.INVITED_EMAIL, verified=False, primary=True)

        # Simulate verification GET
        key = EmailConfirmationHMAC(email_addr).key
        # Persist confirmation token as it would be created by the adapter
        GenericTokenModel.objects.create(user=invited, token=hash_token(key), purpose=INVITATION)
        verify_url = reverse('account_confirm_email', args=[key])
        verify_resp = self.client.get(verify_url)
        self.assertEqual(verify_resp.status_code, 302)
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertTrue(GenericTokenModel.objects.filter(user=invited, purpose=PASS_SET_ACCESS).exists())

        # Set password
        response = self.client.post(
            self.set_password_url,
            data={"new_password1": "A-1_newpass", "new_password2": "A-1_newpass"},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.json())
        self.assertIn(REFRESH_TOKEN_COOKIE, response.cookies)

        # Login works
        login_response = self.client.post(
            self.login_url,
            data={"email": self.INVITED_EMAIL, "password": "A-1_newpass"},
            content_type='application/json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.json())


@override_settings(
    JWT_ALLAUTH_INVITATIONS=True,
    EMAIL_VERIFICATION=True,
    PASSWORD_SET_REDIRECT='/set-password-ui/',
    ROOT_URLCONF='tests.django_urls')
class InvitationsAlongsideOpenRegistrationTests(TestsMixin):
    """
    Invitations added to a project that keeps its public sign-up.

    ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` has always meant invitations *instead of*
    open registration, which rules out the ordinary shape of a product: customers sign
    themselves up and staff are invited. ``JWT_ALLAUTH_INVITATIONS`` adds the second way
    in without taking the first one away.
    """

    INVITED_EMAIL = 'invited@demo.com'
    SELF_EMAIL = 'self.signup@demo.com'

    def setUp(self):
        clear_url_caches()
        from importlib import reload
        import jwt_allauth.registration.urls
        import jwt_allauth.urls
        import tests.django_urls
        reload(jwt_allauth.registration.urls)
        reload(jwt_allauth.urls)
        reload(tests.django_urls)

        self.init()
        self.user_register_url = reverse('rest_user_register')
        self.set_password_url = reverse('rest_set_password')

    def tearDown(self):
        clear_url_caches()
        from importlib import reload
        import jwt_allauth.registration.urls
        import jwt_allauth.urls
        import tests.django_urls
        reload(jwt_allauth.registration.urls)
        reload(jwt_allauth.urls)
        reload(tests.django_urls)

    def test_both_ways_in_are_routed(self):
        self.assertTrue(reverse('rest_register'))
        self.assertTrue(reverse('rest_user_register'))

    def test_public_sign_up_still_works(self):
        """The regression that matters: adding invitations must not close the door."""
        resp = self.client.post(
            reverse('rest_register'),
            data={
                'email': self.SELF_EMAIL,
                'password1': 'A-1_newpass',
                'password2': 'A-1_newpass',
                'first_name': self.FIRST_NAME,
                'last_name': self.LAST_NAME,
            },
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(get_user_model().objects.filter(email=self.SELF_EMAIL).exists())

    def _invite(self):
        self.token = str(RefreshToken.for_user(self.USER).access_token)
        self.USER.is_staff = True
        self.USER.save()
        return self.client.post(
            self.user_register_url,
            data={'email': self.INVITED_EMAIL, 'first_name': 'In', 'last_name': 'Vited'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )

    def test_invitation_flow_completes(self):
        invited = get_user_model().objects.create_user('invited', email=self.INVITED_EMAIL)
        address = EmailAddress.objects.create(
            user=invited, email=self.INVITED_EMAIL, verified=False, primary=True)
        key = EmailConfirmationHMAC(address).key
        GenericTokenModel.objects.create(user=invited, token=hash_token(key), purpose=INVITATION)

        verify = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(verify.status_code, 302)
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)

        resp = self.client.post(
            self.set_password_url,
            data={'new_password1': 'A-1_newpass', 'new_password2': 'A-1_newpass'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.json())

    @override_settings(JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION=True)
    def test_a_self_registered_confirmation_is_not_treated_as_an_invitation(self):
        """
        Both flows arrive through the same link, and the password is what tells them
        apart. A sign-up that chose a password has to go through the ordinary
        confirmation -- which enables the session registration left disabled and, under
        ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION``, hands one out. The invitation path
        does neither, so mistaking one for the other silently breaks sign-up.
        """
        signed_up = get_user_model().objects.create_user(
            'selfsignup', email=self.SELF_EMAIL, password='A-1_newpass')
        address = EmailAddress.objects.create(
            user=signed_up, email=self.SELF_EMAIL, verified=False, primary=True)
        pending = RefreshToken.for_user(signed_up, enabled=False)
        key = EmailConfirmationHMAC(address).key
        GenericTokenModel.objects.create(user=signed_up, token=hash_token(key), purpose=EMAIL_CONFIRMATION)

        verify = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(verify.status_code, 302)
        self.assertNotIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertFalse(
            GenericTokenModel.objects.filter(user=signed_up, purpose=PASS_SET_ACCESS).exists())
        address.refresh_from_db()
        self.assertTrue(address.verified)

        # The two assertions that only the ordinary confirmation satisfies.
        self.assertTrue(
            RefreshTokenWhitelistModel.objects.get(jti=pending.payload['jti']).enabled)
        self.assertIn(REFRESH_TOKEN_COOKIE, verify.cookies)

    def test_a_confirmation_with_no_invitation_behind_it_still_confirms(self):
        """
        With registration closed a key with no row behind it is refused. With sign-up
        open it is an ordinary confirmation, and refusing it would break registration.
        """
        signed_up = get_user_model().objects.create_user(
            'nolinkrow', email=self.SELF_EMAIL, password='A-1_newpass')
        address = EmailAddress.objects.create(
            user=signed_up, email=self.SELF_EMAIL, verified=False, primary=True)
        key = EmailConfirmationHMAC(address).key

        verify = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(verify.status_code, 302)
        address.refresh_from_db()
        self.assertTrue(address.verified)

    def test_social_signup_stays_open(self):
        """Only closed registration shuts social sign-up; invitations do not."""
        from jwt_allauth.social.adapter import JWTAllAuthSocialAccountAdapter
        self.assertTrue(JWTAllAuthSocialAccountAdapter().is_open_for_signup(None, None))


@override_settings(
    JWT_ALLAUTH_INVITATIONS=True,
    EMAIL_VERIFICATION=True,
    PASSWORD_SET_REDIRECT='/set-password-ui/',
    ROOT_URLCONF='tests.django_urls')
class InvitationReservesTheAddressTests(TestsMixin):
    """
    An invitation in flight holds on to the address it was sent to.

    An invited account is indistinguishable from an abandoned sign-up by shape alone --
    no password, never used, address unconfirmed -- so before the invitation was recorded
    as such, anybody could post the invitee's address to the public sign-up and destroy
    the account, the role granted with it and the link, silently. The reservation lasts
    exactly as long as the link does: a dead invitation must not keep an address hostage.
    """

    INVITED_EMAIL = 'invited@demo.com'

    def setUp(self):
        clear_url_caches()
        from importlib import reload
        import jwt_allauth.registration.urls
        import jwt_allauth.urls
        import tests.django_urls
        reload(jwt_allauth.registration.urls)
        reload(jwt_allauth.urls)
        reload(tests.django_urls)

        self.init()
        self.register_url = reverse('rest_register')

    def tearDown(self):
        clear_url_caches()
        from importlib import reload
        import jwt_allauth.registration.urls
        import jwt_allauth.urls
        import tests.django_urls
        reload(jwt_allauth.registration.urls)
        reload(jwt_allauth.urls)
        reload(tests.django_urls)

    def _invite(self, age_days=0):
        """An invited account with its link either still live or long expired."""
        invited = get_user_model().objects.create_user('invited', email=self.INVITED_EMAIL)
        invited.set_unusable_password()
        invited.save()
        address = EmailAddress.objects.create(
            user=invited, email=self.INVITED_EMAIL, verified=False, primary=True)
        key = EmailConfirmationHMAC(address).key
        token = GenericTokenModel.objects.create(
            user=invited, token=hash_token(key), purpose=INVITATION)
        if age_days:
            GenericTokenModel.objects.filter(pk=token.pk).update(
                created=timezone.now() - timedelta(days=age_days))
        return invited, key

    def _sign_up(self):
        return self.client.post(
            self.register_url,
            data={
                'email': self.INVITED_EMAIL,
                'password1': 'A-1_newpass',
                'password2': 'A-1_newpass',
                'first_name': self.FIRST_NAME,
                'last_name': self.LAST_NAME,
            },
            content_type='application/json',
        )

    def test_a_public_sign_up_does_not_destroy_a_live_invitation(self):
        invited, key = self._invite()

        resp = self._sign_up()

        # The conflict is hidden, so the caller is told nothing either way.
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(get_user_model().objects.filter(pk=invited.pk).exists())
        self.assertEqual(
            get_user_model().objects.filter(email=self.INVITED_EMAIL).count(), 1)
        # The link still works, and still leads to the password-set capability.
        verify = self.client.get(reverse('account_confirm_email', args=[key]))
        self.assertEqual(verify.status_code, 302)
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)

    def test_an_expired_invitation_frees_the_address(self):
        invited, _ = self._invite(
            age_days=allauth_app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS + 1)

        resp = self._sign_up()

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(get_user_model().objects.filter(pk=invited.pk).exists())
        self.assertEqual(
            get_user_model().objects.filter(email=self.INVITED_EMAIL).count(), 1)

    def test_a_password_less_account_without_an_invitation_is_not_invited(self):
        """
        An account created by a social provider has no usable password either, which is
        what an invitation used to be recognised by. Handing that account's confirmation
        link the password-set capability turns any provider's mail into a way of setting
        a local password on it.
        """
        social_like = get_user_model().objects.create_user(
            'socially', email='social.signup@demo.com')
        social_like.set_unusable_password()
        social_like.save()
        address = EmailAddress.objects.create(
            user=social_like, email=social_like.email, verified=False, primary=True)
        key = EmailConfirmationHMAC(address).key
        GenericTokenModel.objects.create(
            user=social_like, token=hash_token(key), purpose=EMAIL_CONFIRMATION)

        verify = self.client.get(reverse('account_confirm_email', args=[key]))

        self.assertEqual(verify.status_code, 302)
        self.assertNotIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertFalse(
            GenericTokenModel.objects.filter(user=social_like, purpose=PASS_SET_ACCESS).exists())
        address.refresh_from_db()
        self.assertTrue(address.verified)
