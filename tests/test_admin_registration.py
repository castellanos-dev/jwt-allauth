from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import NoReverseMatch, clear_url_caches, reverse
from rest_framework import status

from jwt_allauth.constants import (
    SET_PASSWORD_COOKIE,
    PASS_SET_ACCESS,
    REFRESH_TOKEN_COOKIE,
    EMAIL_CONFIRMATION,
)
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel
from .mixins import TestsMixin


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
        When a staff user registers an invited user, a confirmation token
        should be persisted for EMAIL_CONFIRMATION with the correct key.
        """
        staff = get_user_model().objects.create_user(
            'admin_token', email='admin_token@demo.com', password='A-1_strong', is_staff=True
        )
        EmailAddress.objects.create(user=staff, email=staff.email, verified=True, primary=True)
        staff_access = str(RefreshToken.for_user(staff).access_token)

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

        key = EmailConfirmationHMAC(email_addr).key

        token = GenericTokenModel.objects.filter(user=invited, purpose=EMAIL_CONFIRMATION).first()
        self.assertIsNotNone(token)
        self.assertEqual(token.token, key)

    def test_email_confirmation_token_single_use(self):
        """
        The EMAIL_CONFIRMATION token must be single-use: first GET succeeds,
        second GET with the same key must fail with 401.
        """
        invited = get_user_model().objects.create_user('invited_single_use', email=self.INVITED_EMAIL)
        email_addr = EmailAddress.objects.create(
            user=invited, email=self.INVITED_EMAIL, verified=False, primary=True
        )

        key = EmailConfirmationHMAC(email_addr).key
        GenericTokenModel.objects.create(user=invited, token=key, purpose=EMAIL_CONFIRMATION)

        verify_url = reverse('account_confirm_email', args=[key])

        # First use: token is valid and should be consumed
        first_resp = self.client.get(verify_url)
        self.assertEqual(first_resp.status_code, 302)
        self.assertIn(SET_PASSWORD_COOKIE, self.client.cookies)
        self.assertFalse(
            GenericTokenModel.objects.filter(
                user=invited, token=key, purpose=EMAIL_CONFIRMATION
            ).exists()
        )
        self.assertTrue(
            GenericTokenModel.objects.filter(user=invited, purpose=PASS_SET_ACCESS).exists()
        )

        # Second use: token was consumed, so this must fail
        before_pass_set_tokens = GenericTokenModel.objects.filter(
            user=invited, purpose=PASS_SET_ACCESS
        ).count()
        second_resp = self.client.get(verify_url)
        self.assertEqual(second_resp.status_code, status.HTTP_401_UNAUTHORIZED)
        after_pass_set_tokens = GenericTokenModel.objects.filter(
            user=invited, purpose=PASS_SET_ACCESS
        ).count()
        self.assertEqual(before_pass_set_tokens, after_pass_set_tokens)

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
        GenericTokenModel.objects.create(user=invited, token=key, purpose=EMAIL_CONFIRMATION)
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
        GenericTokenModel.objects.create(user=invited, token=key, purpose=EMAIL_CONFIRMATION)
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
