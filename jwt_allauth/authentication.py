"""
Authentication classes with an optional server-side session revocation check.

Access tokens are self-contained: nothing in them tells the server whether the session
they belong to is still alive. Revoking a session removes it from the refresh token
whitelist, which stops rotation, but the access tokens already issued for it stay usable
until they expire on their own.

Setting ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK = True`` closes that window, at the cost
of one indexed query per authenticated request. It is disabled by default: authentication
stays fully stateless and the exposure after a revocation is bounded by
``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME``.
"""

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication, JWTStatelessUserAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.tokens.models import RefreshTokenWhitelistModel

SESSION_CLAIM = 'session'

#: Name of the setting that enables the per-request session revocation check.
SESSION_CHECK_SETTING = 'JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK'


def session_check_enabled() -> bool:
    """
    Whether access tokens must be checked against the refresh token whitelist.

    Read at call time so that ``override_settings`` and runtime changes are honoured.
    """
    return bool(getattr(settings, SESSION_CHECK_SETTING, False))


def session_is_active(session: str) -> bool:
    """
    Whether the given session still holds a whitelisted refresh token.

    Tokens whitelisted with ``enabled=False`` (issued to an account whose email is not
    verified yet) count as active: they are rejected on rotation, not on authentication,
    so that the email verification endpoints stay reachable.
    """
    return RefreshTokenWhitelistModel.objects.filter(session=session).exists()


def validate_session(validated_token) -> None:
    """
    Reject an access token whose session has been revoked.

    Does nothing unless ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`` is enabled.

    Tokens without a ``session`` claim are left untouched. Those are not session tokens:
    the one-time capabilities issued by the password reset and email confirmation flows
    carry their own single-use validation, and applications minting tokens outside of
    ``RefreshToken.for_user`` have nothing to check them against.

    Raises:
        InvalidToken: if the session behind the token is no longer whitelisted.
    """
    if not session_check_enabled():
        return

    session = validated_token.payload.get(SESSION_CLAIM)
    if session is None:
        return

    if not session_is_active(session):
        raise InvalidToken(_('Session is no longer active.'))


class SessionRevocationMixin:
    """
    Mixin adding the session revocation check to a simplejwt authentication class.

    Combine it with any ``JWTAuthentication`` subclass to make revocation effective on
    access tokens too:

    .. code-block:: python

        class MyAuthentication(SessionRevocationMixin, JWTAuthentication):
            pass
    """

    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        validate_session(validated_token)
        return validated_token


class JWTAllAuthAuthentication(SessionRevocationMixin, JWTStatelessUserAuthentication):
    """
    Default authentication class.

    Keeps the stateless user of ``JWTStatelessUserAuthentication`` — the user is built
    from the token claims, the user table is never hit — and applies the session
    revocation check when ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`` is enabled.
    """


class JWTAllAuthDBAuthentication(SessionRevocationMixin, JWTAuthentication):
    """
    Same behaviour as :class:`JWTAllAuthAuthentication`, on top of the simplejwt
    authentication class that loads the user from the database.
    """
