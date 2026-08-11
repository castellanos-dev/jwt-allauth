from typing import Any, Dict

from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.constants import SESSION_IAT_CLAIM
from jwt_allauth.exceptions import SessionExpired
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.serializers import RefreshTokenWhitelistSerializer
from jwt_allauth.utils import is_email_verified

# Reasons for which a rotation is turned down.
REPLAYED = 'replayed'
DISABLED = 'disabled'
SESSION_EXPIRED = 'session_expired'
INACTIVE_USER = 'inactive_user'


class RotationRejected(Exception):
    """
    Internal signal raised from within the rotation transaction.

    Every rejection revokes something, and that revocation has to outlive the
    rollback of the transaction it is detected in. Rejections therefore travel out of
    the atomic block as this exception and are turned into the client-facing error by
    ``TokenRefreshSerializer.reject`` once the transaction has been unwound.
    """

    def __init__(self, reason, user=None):
        super().__init__(reason)
        self.reason = reason
        self.user = user


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)
    token_class = RefreshToken

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        refresh = self.token_class(attrs["refresh"])

        try:
            with transaction.atomic():
                data = self.rotate(refresh)
        except RotationRejected as rejection:
            self.reject(refresh, rejection)

        del attrs["refresh"]

        return data

    def rotate(self, refresh) -> Dict[str, str]:
        """
        Consume the presented refresh token and hand out its successor.

        Must run inside a transaction: the whitelist row is locked before it is read so
        that two requests carrying the same credential cannot both pass the whitelist
        check, delete the entry and insert a successor, which would turn a single
        credential into two live sessions and hide the replay from the detection below.
        """
        query_set = list(RefreshTokenWhitelistModel.objects.select_for_update().filter(jti=refresh.payload["jti"]))
        if len(query_set) == 0:
            raise RotationRejected(REPLAYED)
        if not query_set[0].enabled:
            raise RotationRejected(DISABLED, query_set[0].user)

        if SESSION_IAT_CLAIM not in refresh.payload:
            # Token issued before absolute session lifetimes existed: the session start is
            # unknown, so it is anchored at this first rotation.
            refresh.set_session_iat()
        elif refresh.session_expired():
            # Rotation cannot extend a session past its absolute lifetime: the whole
            # session is revoked and the user has to authenticate again.
            raise RotationRejected(SESSION_EXPIRED)

        user = query_set[0].user
        if not user.is_active:
            # Deactivated accounts must not be able to keep rotating tokens.
            raise RotationRejected(INACTIVE_USER, user)

        # Re-read the privileges from the database so that role changes are not
        # carried over from the old token.
        refresh.sync_user_claims(user)

        data = {"access": str(refresh.access_token)}

        # Claim the credential. The row lock above serialises the concurrent rotations
        # that reach this point, and the reported delete count is the portable fallback
        # on backends without row locking: only the request that actually removed the
        # entry is allowed to mint the successor.
        deleted, _ = RefreshTokenWhitelistModel.objects.filter(pk=query_set[0].pk).delete()
        if deleted == 0:
            raise RotationRejected(REPLAYED)

        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()
        refresh.cap_exp_to_session()

        data["refresh"] = str(refresh)

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
            # Backstop for the unique constraint on `jti`: reached when a concurrent
            # insert slips between the serializer's uniqueness check and this write.
            raise InvalidToken("Failed to persist rotated refresh token.") from exc

        return data

    @staticmethod
    def reject(refresh, rejection: RotationRejected):
        """
        Apply the revocation the rejection calls for and raise the client-facing error.

        Runs outside of the rotation transaction so that the revocation is committed
        even though the request itself fails.
        """
        if rejection.reason == REPLAYED:
            # Suspicious operation: the credential is not whitelisted, so it was either
            # already rotated or forged. The whole session goes down.
            RefreshTokenWhitelistModel.objects.filter(session=refresh.payload["session"]).delete()
            raise InvalidToken()
        if rejection.reason == DISABLED:
            is_email_verified(rejection.user, raise_exception=True)
            raise InvalidToken()
        if rejection.reason == SESSION_EXPIRED:
            RefreshTokenWhitelistModel.objects.filter(session=refresh.payload["session"]).delete()
            raise SessionExpired()
        RefreshTokenWhitelistModel.objects.filter(user=rejection.user).delete()
        raise InvalidToken()
