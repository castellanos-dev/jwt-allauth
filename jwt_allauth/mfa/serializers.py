from rest_framework import serializers


try:
    from allauth.mfa.models import Authenticator as AuthModel  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    AuthModel = None  # type: ignore


class MFAActivateSerializer(serializers.Serializer):
    """
    Activates TOTP for the authenticated user by providing a 6-digit code.

    Can be used in two ways:
    - With JWT authentication (normal case)
    - With setup_challenge_id (bootstrap MFA after login when REQUIRED mode)
    """
    code = serializers.CharField(min_length=6, max_length=6)
    setup_challenge_id = serializers.CharField(required=False, allow_blank=True)


class MFAVerifySerializer(serializers.Serializer):
    """
    Verifies a TOTP code during login using a server-side challenge.
    """
    challenge_id = serializers.CharField()
    code = serializers.CharField(min_length=6, max_length=6)


class MFAVerifyRecoverySerializer(serializers.Serializer):
    """
    Verifies a recovery code during login using a server-side challenge.
    """
    challenge_id = serializers.CharField()
    recovery_code = serializers.CharField()


class MFADeactivateSerializer(serializers.Serializer):
    """
    Deactivates TOTP for the authenticated user.
    """
    password = serializers.CharField(write_only=True)


if AuthModel is not None:
    class AuthenticatorSerializer(serializers.ModelSerializer):  # type: ignore[misc]
        class Meta:
            model = AuthModel
            fields = ("id", "type", "created_at", "last_used_at")
            read_only_fields = fields
else:
    class AuthenticatorSerializer(serializers.Serializer):
        """
        Fallback serializer when allauth.mfa is not available.
        """
        id = serializers.IntegerField()
        type = serializers.CharField()
        created_at = serializers.DateTimeField()
        last_used_at = serializers.DateTimeField(allow_null=True)
