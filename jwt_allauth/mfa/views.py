from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jwt_allauth.constants import (
    MFA_TOKEN_MAX_AGE_SECONDS,
    MFA_TOTP_DISABLED,
    MFA_TOTP_REQUIRED,
)

from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.utils import build_token_response
from .serializers import (
    MFAActivateSerializer,
    MFAVerifySerializer,
    MFAVerifyRecoverySerializer,
    MFADeactivateSerializer,
    AuthenticatorSerializer,
)
from jwt_allauth.utils import load_user


def get_mfa_totp_mode() -> str:
    """
    Return the current MFA TOTP mode from settings.

    This must be evaluated at call time (not import time) so that
    Django's `override_settings` used in tests – and any runtime changes
    – are respected.
    """
    return getattr(settings, "JWT_ALLAUTH_MFA_TOTP_MODE", MFA_TOTP_DISABLED)

try:
    from allauth.mfa.models import Authenticator
    from allauth.mfa.totp.internal.auth import generate_totp_secret, TOTP
    from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
    from allauth.mfa.adapter import get_adapter
except Exception:  # pragma: no cover - optional dependency guard
    Authenticator = None  # type: ignore
    RecoveryCodes = None  # type: ignore
    generate_totp_secret = None  # type: ignore
    TOTP = None  # type: ignore
    get_adapter = None  # type: ignore

    if get_mfa_totp_mode() != MFA_TOTP_DISABLED:
        raise Exception(
            "MFA TOTP is not available. Please ensure 'django-jwt-allauth[mfa]' "
            "is installed and 'allauth.mfa' is added to INSTALLED_APPS."
        )


class MFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    @load_user
    def post(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)

        if Authenticator is None:
            return Response(
                {"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        user = request.user
        if Authenticator.objects.filter(user_id=user.id, type=Authenticator.Type.TOTP.value).exists():
            return Response({"detail": "TOTP already activated."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate TOTP secret using django-allauth's native function
        secret = generate_totp_secret()

        # Store secret in cache with TTL
        cache_key = f"mfa_setup:{user.id}"
        cache.set(cache_key, secret, timeout=MFA_TOKEN_MAX_AGE_SECONDS)

        # Build provisioning URI and QR code using django-allauth's adapter
        adapter = get_adapter()
        provisioning_uri = adapter.build_totp_url(user, secret)
        totp_svg = adapter.build_totp_svg(provisioning_uri)

        return Response({
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": totp_svg,
        })


class MFAActivateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MFAActivateSerializer

    @load_user
    def post(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)

        if Authenticator is None or RecoveryCodes is None:
            return Response(
                {"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Retrieve secret from cache
        cache_key = f"mfa_setup:{request.user.id}"
        secret = cache.get(cache_key)
        if not secret:
            return Response({"detail": "Setup not initiated."}, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data["code"]

        # Create temporary TOTP instance to validate the code
        temp_totp = TOTP.activate(request.user, secret)
        if not temp_totp.validate_code(code):
            # Delete the authenticator if validation fails
            temp_totp.instance.delete()
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete secret from cache after successful verification
        cache.delete(cache_key)

        recovery = RecoveryCodes.activate(request.user)
        recovery_codes = recovery.get_unused_codes()

        return Response({"success": True, "recovery_codes": recovery_codes})


class MFAListAuthenticatorsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)

        if Authenticator is None:
            return Response({"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        authenticators = Authenticator.objects.filter(user_id=request.user.id).order_by("id")
        serializer = AuthenticatorSerializer(authenticators, many=True)
        return Response(serializer.data)


class MFADeactivateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MFADeactivateSerializer

    @load_user
    def post(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)
        if get_mfa_totp_mode() == MFA_TOTP_REQUIRED:
            return Response(
                {"detail": "MFA TOTP is required and cannot be disabled."}, status=status.HTTP_403_FORBIDDEN)

        if Authenticator is None:
            return Response({"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["password"]):
            return Response({"detail": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete both TOTP and recovery code authenticators for the user
        deleted, _ = Authenticator.objects.filter(
            user_id=request.user.id,
            type__in=[
                Authenticator.Type.TOTP.value,
                getattr(Authenticator.Type, "RECOVERY_CODES", Authenticator.Type.RECOVERY_CODES).value
                if hasattr(Authenticator.Type, "RECOVERY_CODES") and hasattr(Authenticator.Type.RECOVERY_CODES, "value")
                else getattr(Authenticator.Type, "RECOVERY_CODES", Authenticator.Type.RECOVERY_CODES)
            ],
        ).delete()
        if deleted == 0:
            return Response({"detail": "TOTP not activated."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True})


class MFAVerifyView(APIView):
    serializer_class = MFAVerifySerializer

    def post(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)
        if Authenticator is None:
            return Response({"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge_id = serializer.validated_data["challenge_id"]
        code = serializer.validated_data["code"]

        # Retrieve challenge from cache
        challenge_data = cache.get(f"mfa_challenge:{challenge_id}")
        if not challenge_data:
            return Response({"detail": "Challenge expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)

        user_id = challenge_data.get("user_id")
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        auth_qs = Authenticator.objects.filter(user_id=user.id, type=Authenticator.Type.TOTP.value)
        if not auth_qs.exists():
            return Response({"detail": "TOTP not activated."}, status=status.HTTP_400_BAD_REQUEST)
        authenticator = auth_qs.first()

        # Validate TOTP code using django-allauth's TOTP class
        totp = TOTP(authenticator)
        if not totp.validate_code(code):
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete challenge after successful verification
        cache.delete(f"mfa_challenge:{challenge_id}")

        refresh = RefreshToken.for_user(user)
        return build_token_response(refresh)


class MFAVerifyRecoveryView(APIView):
    serializer_class = MFAVerifyRecoverySerializer

    def post(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)
        if Authenticator is None or RecoveryCodes is None:
            return Response({"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge_id = serializer.validated_data["challenge_id"]
        recovery_code = serializer.validated_data["recovery_code"]

        # Retrieve challenge from cache
        challenge_data = cache.get(f"mfa_challenge:{challenge_id}")
        if not challenge_data:
            return Response({"detail": "Challenge expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)

        user_id = challenge_data.get("user_id")
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get recovery codes authenticator for the user
        rc_authenticator = Authenticator.objects.filter(
            user_id=user.id, type=Authenticator.Type.RECOVERY_CODES.value
        ).first()
        if not rc_authenticator:
            return Response({"detail": "Recovery codes not available."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate recovery code using django-allauth's RecoveryCodes class
        rc = RecoveryCodes(rc_authenticator)
        if not rc.validate_code(recovery_code):
            return Response({"detail": "Invalid recovery code."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete challenge after successful verification
        cache.delete(f"mfa_challenge:{challenge_id}")

        refresh = RefreshToken.for_user(user)
        return build_token_response(refresh)
