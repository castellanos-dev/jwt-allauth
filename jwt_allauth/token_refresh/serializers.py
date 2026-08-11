from typing import Dict, Any

from django.db import IntegrityError
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

        user = query_set[0].user
        if not user.is_active:
            # Deactivated accounts must not be able to keep rotating tokens.
            RefreshTokenWhitelistModel.objects.filter(user=user).delete()
            raise InvalidToken()

        # Re-read the privileges from the database so that role changes are not
        # carried over from the old token.
        refresh.sync_user_claims(user)

        data = {"access": str(refresh.access_token)}

        RefreshTokenWhitelistModel.objects.filter(jti=refresh.payload["jti"]).delete()

        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()

        data["refresh"] = str(refresh)

        del attrs["refresh"]

        # Get user agent data from context instead of request data
        serializer_data = {
            'jti': refresh.payload['jti'],
            'user': refresh.payload['user_id'],
            'session': refresh.payload['session'],
            **self.context  # Use context data here
        }

        refresh_serializer = RefreshTokenWhitelistSerializer(data=serializer_data)
        refresh_serializer.is_valid(raise_exception=True)
        try:
            refresh_serializer.save()
        except IntegrityError as exc:
            raise InvalidToken("Failed to persist rotated refresh token.") from exc

        return data
