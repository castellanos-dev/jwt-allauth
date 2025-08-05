from unittest.mock import patch

from django.urls import reverse

from jwt_allauth.constants import REFRESH_TOKEN_COOKIE
from jwt_allauth.permissions import BasePermission
from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE
from jwt_allauth.tokens.tokens import RefreshToken
from .mixins import TestsMixin


class CustomUserPermission(BasePermission):
    accepted_roles = [300]


class LoginTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_role_in_token(self):
        self.assertIn("role", self.TOKEN)
        self.assertEqual(self.TOKEN["role"], 0)

    def test_staff_role(self):
        self.USER.is_staff = True
        self.USER.role = STAFF_CODE
        self.USER.save()

        # Generate new token
        login_response = self.client.post(
            reverse("rest_login"),
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        access_token = RefreshToken.access_token_class(login_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)

        # Get refresh token from cookie
        refresh_token_str = login_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

        # Token refreshed - set cookie manually for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh_token_str
        refresh_response = self.client.post(
            reverse("token_refresh"),
            data={},
            format='json'
        )
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        access_token = RefreshToken.access_token_class(refresh_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)

        # Get new refresh token from cookie
        new_refresh_token_str = refresh_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(new_refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

    def test_staff_role_correct_in_tokens(self):
        self.USER.is_staff = True
        self.USER.is_superuser = True
        self.USER.role = STAFF_CODE
        self.USER.save()

        # Generate new token
        login_response = self.client.post(
            reverse("rest_login"),
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        access_token = RefreshToken.access_token_class(login_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)

        # Get refresh token from cookie
        refresh_token_str = login_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

        # Token refreshed - set cookie manually for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh_token_str
        refresh_response = self.client.post(
            reverse("token_refresh"),
            data={},
            format='json'
        )
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        access_token = RefreshToken.access_token_class(refresh_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)

        # Get new refresh token from cookie
        new_refresh_token_str = refresh_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(new_refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

    def test_superuser_role_correct_in_tokens(self):
        self.USER.is_superuser = True
        self.USER.role = SUPER_USER_CODE
        self.USER.save()

        # Generate new token
        login_response = self.client.post(
            reverse("rest_login"),
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        access_token = RefreshToken.access_token_class(login_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], SUPER_USER_CODE)

        # Get refresh token from cookie
        refresh_token_str = login_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], SUPER_USER_CODE)

        # Token refreshed - set cookie manually for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh_token_str
        refresh_response = self.client.post(
            reverse("token_refresh"),
            data={},
            format='json'
        )
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        access_token = RefreshToken.access_token_class(refresh_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], SUPER_USER_CODE)

        # Get new refresh token from cookie
        new_refresh_token_str = refresh_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(new_refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], SUPER_USER_CODE)

    def test_custom_role_code(self):
        self.USER.role = 300
        self.USER.save()

        # Generate new token
        login_response = self.client.post(
            reverse("rest_login"),
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        access_token = RefreshToken.access_token_class(login_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], 300)

        # Get refresh token from cookie
        refresh_token_str = login_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], 300)

        # Token refreshed - set cookie manually for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = refresh_token_str
        refresh_response = self.client.post(
            reverse("token_refresh"),
            data={},
            format='json'
        )
        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        access_token = RefreshToken.access_token_class(refresh_data["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], 300)

        # Get new refresh token from cookie
        new_refresh_token_str = refresh_response.cookies[REFRESH_TOKEN_COOKIE].value
        refresh_token = RefreshToken(new_refresh_token_str)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], 300)

    @patch("jwt_allauth.user_details.views.UserDetailsView.permission_classes", [CustomUserPermission])
    def test_custom_permissions(self):
        self.token = self.ACCESS
        self.get(self.user_url, status_code=403)

        self.USER.role = 300
        self.USER.save()

        refresh_token = RefreshToken.for_user(self.USER)
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], 300)

        self.token = str(refresh_token.access_token)
        self.get(self.user_url, status_code=200)

    @patch("jwt_allauth.user_details.views.UserDetailsView.permission_classes", [CustomUserPermission])
    def test_custom_permission_denied(self):
        self.USER.role = 200
        self.USER.save()

        resp = self.post(reverse("rest_login"), data=self.LOGIN_PAYLOAD, status_code=200)
        self.token = resp["access"]
        self.get(self.user_url, status_code=403)

    @patch("jwt_allauth.user_details.views.UserDetailsView.permission_classes", [CustomUserPermission])
    def test_missing_role_claim(self):
        self.USER.role = 300
        self.USER.save()

        user = self.USER
        refresh = RefreshToken.for_user(user)
        del refresh.payload['role']
        access_token = str(refresh.access_token)

        self.token = access_token
        self.get(self.user_url, status_code=403)

    def test_create_superuser_with_correct_role(self):
        """Test that create_superuser sets the correct role."""
        from jwt_allauth.models import JAUser
        user = JAUser.objects.create_superuser(
            username='testsuperuser',
            password='testpass123'
        )
        self.assertEqual(user.role, STAFF_CODE)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_with_wrong_role_fails(self):
        """Test that create_superuser fails if role is not STAFF_CODE."""
        from jwt_allauth.models import JAUser
        with self.assertRaises(ValueError):
            JAUser.objects.create_superuser(
                username='testsuperuser',
                password='testpass123',
                role=SUPER_USER_CODE
            )

    def test_staff_user_constraint(self):
        """Test that staff users must have STAFF_CODE role."""
        from django.db import IntegrityError
        from jwt_allauth.models import JAUser

        # Create a staff user with wrong role
        with self.assertRaises(IntegrityError):
            JAUser.objects.create_user(
                username='teststaff',
                password='testpass123',
                is_staff=True,
                role=SUPER_USER_CODE
            )
        with self.assertRaises(IntegrityError):
            JAUser.objects.create_user(
                username='teststaff',
                password='testpass123',
                is_staff=False,
                is_superuser=True,
                role=300
            )

    def test_save_method_role_assignment(self):
        """Test that save method correctly assigns roles."""
        from jwt_allauth.models import JAUser

        # Test staff role assignment
        user = JAUser.objects.create_superuser(
            username='teststaff',
            password='testpass123',
        )
        self.assertEqual(user.role, STAFF_CODE)

        # Test superuser role assignment
        user = JAUser.objects.create_user(
            username='testsuper',
            password='testpass123',
            is_superuser=True
        )
        self.assertEqual(user.role, SUPER_USER_CODE)

        # Test that staff role takes precedence over superuser
        user = JAUser.objects.create_user(
            username='testboth',
            password='testpass123',
            is_staff=True
        )
        self.assertEqual(user.role, STAFF_CODE)

    def test_simplified_set_user_role(self):
        """Test that set_user_role now uses the user's role directly."""
        from jwt_allauth.models import JAUser
        from jwt_allauth.tokens.tokens import RefreshToken

        # Create user with custom role
        user = JAUser.objects.create_user(
            username='testcustom',
            password='testpass123',
            role=300
        )

        # Create token and check role
        token = RefreshToken.for_user(user)
        self.assertEqual(token.payload['role'], 300)

        # Change user role and check token
        user.role = 400
        user.save()
        token = RefreshToken.for_user(user)
        self.assertEqual(token.payload['role'], 400)
