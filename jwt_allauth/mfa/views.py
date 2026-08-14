from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from jwt_allauth.constants import (
    MFA_TOTP_DISABLED,
    MFA_TOTP_REQUIRED,
)

from jwt_allauth.throttling import ExtraThrottlesMixin
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.utils import build_token_response, is_email_verified, load_user, verification_is_mandatory
from .serializers import (
    MFAActivateSerializer,
    MFAVerifySerializer,
    MFAVerifyRecoverySerializer,
    MFADeactivateSerializer,
    AuthenticatorSerializer,
)
from jwt_allauth.mfa.gate import get_mfa_totp_mode
from jwt_allauth.mfa.permissions import IsAuthenticatedOrHasMFASetupChallenge
from jwt_allauth.mfa.storage import (
    clear_failed_login_attempts,
    delete_login_challenge,
    delete_setup_challenge,
    delete_setup_secret,
    get_login_challenge_user,
    load_setup_secret,
    login_lockout_remaining,
    record_failed_login_attempt,
    store_setup_secret,
)


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


class MFASetupView(ExtraThrottlesMixin, APIView):
    """
    Start TOTP enrolment: returns the secret, its provisioning URI and a QR code.

    Authorized by the session, or by the ``setup_challenge_id`` handed out when MFA is
    required and the account has none configured yet. The authenticator is not active
    until ``/mfa/activate/`` confirms a code from it.
    """
    permission_classes = [IsAuthenticatedOrHasMFASetupChallenge]
    extra_throttle_classes = (AnonRateThrottle, UserRateThrottle)

    def post(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)

        if Authenticator is None:
            return Response(
                {"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        # Determine user: JWT auth or MFA setup bootstrap
        if request.user and request.user.is_authenticated:
            user = get_user_model().objects.get(id=request.user.id)
        elif hasattr(request, "mfa_setup_user"):
            user = request.mfa_setup_user
        else:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if Authenticator.objects.filter(user_id=user.id, type=Authenticator.Type.TOTP.value).exists():
            return Response({"detail": "TOTP already activated."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate TOTP secret using django-allauth's native function
        secret = generate_totp_secret()

        # Store secret using MFA storage backend
        store_setup_secret(user.id, secret)

        # Build provisioning URI and QR code using django-allauth's adapter
        adapter = get_adapter()
        provisioning_uri = adapter.build_totp_url(user, secret)
        totp_svg = adapter.build_totp_svg(provisioning_uri)

        return Response({
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": totp_svg,
        })


class MFAActivateView(ExtraThrottlesMixin, APIView):
    """
    Confirm a code from the authenticator being enrolled and activate it.

    Returns the recovery codes, which are shown once and never again. When the
    enrolment was bootstrapped from a setup challenge, it also opens the session the
    account was waiting on.
    """
    permission_classes = [IsAuthenticatedOrHasMFASetupChallenge]
    serializer_class = MFAActivateSerializer
    extra_throttle_classes = (AnonRateThrottle, UserRateThrottle)

    def post(self, request: Request) -> Response:
        if get_mfa_totp_mode() == MFA_TOTP_DISABLED:
            return Response(
                {"detail": "MFA TOTP is disabled."}, status=status.HTTP_403_FORBIDDEN)

        if Authenticator is None or RecoveryCodes is None:
            return Response(
                {"detail": "allauth.mfa is not installed."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Determine user: JWT auth or MFA setup bootstrap
        if request.user and request.user.is_authenticated:
            user = get_user_model().objects.get(id=request.user.id)
        elif hasattr(request, "mfa_setup_user"):
            user = request.mfa_setup_user
        else:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Retrieve secret from MFA storage backend
        secret = load_setup_secret(user.id)
        if not secret:
            return Response({"detail": "Setup not initiated."}, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data["code"]

        # Create temporary TOTP instance to validate the code
        temp_totp = TOTP.activate(user, secret)
        if not temp_totp.validate_code(code):
            # Delete the authenticator if validation fails
            temp_totp.instance.delete()
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete secret after successful verification
        delete_setup_secret(user.id)

        recovery = RecoveryCodes.activate(user)
        recovery_codes = recovery.get_unused_codes()

        # Clean up setup_challenge if provided
        setup_challenge_id = serializer.validated_data.get("setup_challenge_id")
        is_bootstrap = bool(setup_challenge_id)
        if setup_challenge_id:
            delete_setup_challenge(setup_challenge_id)

        # If this is a bootstrap flow in REQUIRED mode (setup_challenge_id present),
        # issue tokens for immediate login/registration completion.
        # This covers both login bootstrap and registration bootstrap flows.
        if is_bootstrap and get_mfa_totp_mode() == MFA_TOTP_REQUIRED:
            # Registration hands the setup challenge to an anonymous caller before the
            # address is confirmed, so the bootstrap must not grant a session that
            # mandatory verification withholds. Login and set-password already require a
            # verified address and are unaffected, and under
            # ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` there is no session to
            # withhold: registration itself hands one out.
            verification_pending = verification_is_mandatory() and not is_email_verified(user)

            refresh = RefreshToken.for_user(user, enabled=not verification_pending)

            if verification_pending:
                # Same shape as RegisterView.get_response_data: disabled refresh token,
                # no access token until the verification link is used.
                return Response(
                    {
                        "success": True,
                        "recovery_codes": recovery_codes,
                        "detail": _("Verification e-mail sent."),
                        "refresh": str(refresh),
                    },
                    status=status.HTTP_200_OK,
                )

            # Use build_token_response to respect cookie configuration
            return build_token_response(
                refresh_token=refresh,
                extra_data={"success": True, "recovery_codes": recovery_codes},
                http_status=status.HTTP_200_OK
            )

        # Normal mode: just return success and recovery codes
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


def _locked_out_response(retry_after: int) -> Response:
    response = Response(
        {"detail": "Too many failed MFA attempts. Try again later."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    response["Retry-After"] = str(retry_after)
    return response


class MFAVerifyView(ExtraThrottlesMixin, APIView):
    """
    Complete a login with a TOTP code and open the session.

    Takes the ``challenge_id`` returned by ``/login/`` and the current code. Answers
    like ``/login/`` does: access token in the body, refresh token as a cookie.
    """
    serializer_class = MFAVerifySerializer
    extra_throttle_classes = (AnonRateThrottle,)

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

        # Retrieve challenge from MFA storage backend
        user = get_login_challenge_user(challenge_id)
        if not user:
            return Response({"detail": "Challenge expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)

        # Refuse to check codes at all while the user is locked out, so a lockout cannot be
        # waited out with a fresh challenge.
        retry_after = login_lockout_remaining(user.id)
        if retry_after:
            return _locked_out_response(retry_after)

        auth_qs = Authenticator.objects.filter(user_id=user.id, type=Authenticator.Type.TOTP.value)
        if not auth_qs.exists():
            return Response({"detail": "TOTP not activated."}, status=status.HTTP_400_BAD_REQUEST)
        authenticator = auth_qs.first()

        # Validate TOTP code using django-allauth's TOTP class
        totp = TOTP(authenticator)
        if not totp.validate_code(code):
            result = record_failed_login_attempt(challenge_id, user)
            if result.locked_out:
                return _locked_out_response(result.retry_after)
            if result.challenge_invalidated:
                return Response({"detail": "Too many failed attempts. Challenge invalidated."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete challenge and reset the attempt counter after successful verification
        delete_login_challenge(challenge_id)
        clear_failed_login_attempts(user.id)

        refresh = RefreshToken.for_user(user)
        return build_token_response(refresh)


class MFAVerifyRecoveryView(ExtraThrottlesMixin, APIView):
    """
    Complete a login with a recovery code and open the session.

    The same as ``/mfa/verify/`` for an authenticator that is out of reach. Each code
    is spent by the request that uses it.
    """
    serializer_class = MFAVerifyRecoverySerializer
    extra_throttle_classes = (AnonRateThrottle,)

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

        # Retrieve challenge from MFA storage backend
        user = get_login_challenge_user(challenge_id)
        if not user:
            return Response({"detail": "Challenge expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)

        retry_after = login_lockout_remaining(user.id)
        if retry_after:
            return _locked_out_response(retry_after)

        # Get recovery codes authenticator for the user
        rc_authenticator = Authenticator.objects.filter(
            user_id=user.id, type=Authenticator.Type.RECOVERY_CODES.value
        ).first()
        if not rc_authenticator:
            return Response({"detail": "Recovery codes not available."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate recovery code using django-allauth's RecoveryCodes class
        rc = RecoveryCodes(rc_authenticator)
        if not rc.validate_code(recovery_code):
            result = record_failed_login_attempt(challenge_id, user)
            if result.locked_out:
                return _locked_out_response(result.retry_after)
            if result.challenge_invalidated:
                return Response({"detail": "Too many failed attempts. Challenge invalidated."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": "Invalid recovery code."}, status=status.HTTP_400_BAD_REQUEST)

        # Delete challenge and reset the attempt counter after successful verification
        delete_login_challenge(challenge_id)
        clear_failed_login_attempts(user.id)

        refresh = RefreshToken.for_user(user)
        return build_token_response(refresh)
