from typing import Dict, Any

from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from jwt_allauth.constants import (
    MFA_TOTP_DISABLED,
    MFA_TOTP_REQUIRED,
)
from jwt_allauth.mfa.storage import (
    create_login_challenge,
    create_setup_challenge,
)
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.utils import allauth_authenticate
from jwt_allauth import app_settings


def get_mfa_totp_mode() -> str:
    """
    Return the current MFA TOTP mode from settings.

    This must be evaluated at call time (not import time) so that
    Django's `override_settings` used in tests – and any runtime changes
    – are respected.
    """
    return app_settings.MFA_TOTP_MODE

try:
    from allauth.mfa.models import Authenticator  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    Authenticator = None  # type: ignore
    if get_mfa_totp_mode() != MFA_TOTP_DISABLED:
        raise Exception(
            "MFA TOTP is not available. Please ensure 'django-jwt-allauth[mfa]' "
            "is installed and 'allauth.mfa' is added to INSTALLED_APPS."
        )


class BaseLoginSerializer(TokenObtainPairSerializer):
    token_class = RefreshToken
    user = None

    def build_authenticate_kwargs(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def get_token(cls, user) -> RefreshToken:
        """
        Instantiates a new TokenObtainPairSerializer object, sets a token for the given user and returns the token.
        """
        cls.token = cls.token_class.for_user(user)
        return cls.token  # type: ignore

    @transaction.atomic
    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        authenticate_kwargs = self.build_authenticate_kwargs(attrs)

        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        # User authentication (allauth)
        self.user = allauth_authenticate(**authenticate_kwargs)

        # Active account check
        if not api_settings.USER_AUTHENTICATION_RULE(self.user):
            raise exceptions.AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        # MFA TOTP check
        mfa_mode = get_mfa_totp_mode()
        if mfa_mode != MFA_TOTP_DISABLED and Authenticator is not None:
            has_mfa = Authenticator.objects.filter(
                user=self.user,
                type=getattr(Authenticator, "Type").TOTP if hasattr(Authenticator, "Type") else "totp",
            ).exists()

            # If MFA is REQUIRED, user must have MFA enabled
            # Instead of raising 403, return setup challenge for bootstrap
            if mfa_mode == MFA_TOTP_REQUIRED and not has_mfa:
                setup_challenge_id = create_setup_challenge(self.user.id)
                return {
                    "mfa_setup_required": True,
                    "setup_challenge_id": setup_challenge_id,
                }

            # If user has MFA enabled (OPTIONAL or REQUIRED mode), request MFA verification
            if has_mfa:
                # Store MFA challenge server-side using MFA storage backend
                challenge_id = create_login_challenge(self.user.id)
                return {"mfa_required": True, "challenge_id": challenge_id}

        validated_data = super().validate(attrs)

        # Set the refresh token
        refresh = self.get_token(self.user)

        validated_data["refresh"] = str(refresh)
        validated_data["access"] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return validated_data


class EmailLoginSerializer(BaseLoginSerializer):
    username_field = 'email'

    def build_authenticate_kwargs(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        return {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }


class PhoneLoginSerializer(BaseLoginSerializer):
    username_field = 'phone_number'

    def build_authenticate_kwargs(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        # Map phone_number to username for authentication backend since we store phone in username field
        return {
            "username": attrs[self.username_field],
            "password": attrs["password"],
        }


# Backwards compatibility: keep the original name pointing to the email serializer.
# The default selection is handled via app_settings.LoginSerializer.
LoginSerializer = EmailLoginSerializer
