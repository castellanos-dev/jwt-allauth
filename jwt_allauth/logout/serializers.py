from typing import Dict, Any

from django.db.models import Q
from django.utils.crypto import constant_time_compare
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel


class RemoveRefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    user = serializers.CurrentUserDefault()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        refresh = RefreshToken(attrs["refresh"])  # The token is verified
        user_id = self.context.get('user')
        if user_id is None or 'session' not in refresh.payload:
            raise InvalidToken()
        if not constant_time_compare(user_id, refresh.payload['user_id']):
            raise InvalidToken()
        query = RefreshTokenWhitelistModel.objects.filter(
            Q(jti=refresh.payload["jti"]) | Q(session=refresh.payload["session"])
        )
        if not query.count() > 0:
            raise InvalidToken()
        query.delete()
        return {}
