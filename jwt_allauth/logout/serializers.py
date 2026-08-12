from typing import Dict, Any

from django.db.models import Q
from django.utils.crypto import constant_time_compare
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.utils import user_sessions_lock


class RemoveRefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    user = serializers.CurrentUserDefault()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        refresh = RefreshToken(attrs["refresh"])  # The token is verified
        user_id = self.context.get('user')
        if user_id is None or 'session' not in refresh.payload:
            raise InvalidToken()
        if not constant_time_compare(str(user_id), str(refresh.payload['user_id'])):
            raise InvalidToken()
        # The successor a concurrent rotation mints carries the same session, so the
        # deletion has to be ordered against it: without the lock the rotation inserts a
        # row this query cannot see and the session stays open past the logout.
        with user_sessions_lock(user_id):
            query = RefreshTokenWhitelistModel.objects.filter(
                Q(jti=refresh.payload["jti"]) | Q(session=refresh.payload["session"])
            )
            if not query.count() > 0:
                raise InvalidToken()
            query.delete()
        return {}
