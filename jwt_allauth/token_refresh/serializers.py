from typing import Dict, Any

from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.serializers import RefreshTokenWhitelistSerializer
from jwt_allauth.utils import is_email_verified


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)
    token_class = RefreshToken
    ip = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_mobile = serializers.BooleanField(required=False, allow_null=True)
    is_tablet = serializers.BooleanField(required=False, allow_null=True)
    is_pc = serializers.BooleanField(required=False, allow_null=True)
    is_bot = serializers.BooleanField(required=False, allow_null=True)
    browser = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    browser_version = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    os = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    os_version = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    device = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    device_brand = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    device_model = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        refresh = self.token_class(attrs["refresh"])

        query_set = list(RefreshTokenWhitelistModel.objects.filter(jti=refresh.payload["jti"]).all())
        if len(query_set) == 0:
            # Suspicious operation
            RefreshTokenWhitelistModel.objects.filter(session=refresh.payload["session"]).delete()
            raise InvalidToken()
        if not query_set[0].enabled:
            is_email_verified(query_set[0].user, raise_exception=True)
            raise InvalidToken()

        data = {"access": str(refresh.access_token)}

        RefreshTokenWhitelistModel.objects.filter(jti=refresh.payload["jti"]).delete()

        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()

        data["refresh"] = str(refresh)

        del attrs["refresh"]

        serializer_data = {
            'jti': refresh.payload['jti'],
            'user': refresh.payload['user_id'],
            'session': refresh.payload['session'],
            **attrs
        }

        refresh_serializer = RefreshTokenWhitelistSerializer(data=serializer_data)
        if refresh_serializer.is_valid():
            refresh_serializer.save()

        return data
