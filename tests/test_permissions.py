from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from jwt_allauth.permissions import BasePermission
from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE
from jwt_allauth.token.tokens import RefreshToken
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
        self.USER.save()

        # Generate new token
        resp = self.post(reverse("rest_login"), data=self.LOGIN_PAYLOAD, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

        # Token refreshed
        resp = self.post(reverse("token_refresh"), data={"refresh": resp["refresh"]}, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)
        self.assertIn("refresh", resp)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

    def test_staff_role_over_other_roles(self):
        self.USER.is_staff = True
        self.USER.is_superuser = True
        self.USER.save()

        # Generate new token
        resp = self.post(reverse("rest_login"), data=self.LOGIN_PAYLOAD, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

        # Token refreshed
        resp = self.post(reverse("token_refresh"), data={"refresh": resp["refresh"]}, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)
        self.assertIn("refresh", resp)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

        self.USER.is_staff = True
        self.USER.is_superuser = False
        self.USER.role = 300
        self.USER.save()

        # Generate new token
        resp = self.post(reverse("rest_login"), data=self.LOGIN_PAYLOAD, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

        # Token refreshed
        resp = self.post(reverse("token_refresh"), data={"refresh": resp["refresh"]}, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], STAFF_CODE)
        self.assertIn("refresh", resp)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], STAFF_CODE)

    def test_superuser_role(self):
        self.USER.is_superuser = True
        self.USER.save()

        # Generate new token
        resp = self.post(reverse("rest_login"), data=self.LOGIN_PAYLOAD, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], SUPER_USER_CODE)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], SUPER_USER_CODE)

        # Token refreshed
        resp = self.post(reverse("token_refresh"), data={"refresh": resp["refresh"]}, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], SUPER_USER_CODE)
        self.assertIn("refresh", resp)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], SUPER_USER_CODE)

    def test_superuser_over_other_roles(self):
        self.USER.is_superuser = True
        self.USER.role = 300
        self.USER.save()

        # Generate new token
        resp = self.post(reverse("rest_login"), data=self.LOGIN_PAYLOAD, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], SUPER_USER_CODE)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], SUPER_USER_CODE)

        # Token refreshed
        resp = self.post(reverse("token_refresh"), data={"refresh": resp["refresh"]}, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], SUPER_USER_CODE)
        self.assertIn("refresh", resp)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], SUPER_USER_CODE)

    def test_custom_role_code(self):
        self.USER.role = 300
        self.USER.save()

        # Generate new token
        resp = self.post(reverse("rest_login"), data=self.LOGIN_PAYLOAD, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], 300)
        refresh_token = RefreshToken(resp["refresh"])
        self.assertIn("role", refresh_token.payload)
        self.assertEqual(refresh_token.payload["role"], 300)

        # Token refreshed
        resp = self.post(reverse("token_refresh"), data={"refresh": resp["refresh"]}, status_code=200)
        access_token = RefreshToken.access_token_class(resp["access"])
        self.assertIn("role", access_token.payload)
        self.assertEqual(access_token.payload["role"], 300)
        self.assertIn("refresh", resp)
        refresh_token = RefreshToken(resp["refresh"])
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
