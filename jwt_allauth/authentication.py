"""
Authentication classes that enforce server-side session revocation.

Access tokens are self-contained: nothing in them tells the server whether the session
they belong to is still alive. Revoking a session — through ``/logout/``,
``/logout-all/``, a password change, an absolute session lifetime, a deactivated account
or the detection of a reused refresh token — removes the session from the refresh token
whitelist, which stops any further rotation. Without the check implemented here, every
access token already handed out for that session stays usable until it expires on its
own, so an attacker that has just rotated a stolen refresh token keeps a working access
token for up to ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME`` after the theft is detected.

The classes below close that window by verifying, on each authenticated request, that
the ``session`` claim of the access token still matches a whitelisted refresh token.
"""

import warnings

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
    return bool(getattr(settings, SESSION_CHECK_SETTING, True))


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
    from the token claims, the user table is never hit — and adds a single indexed query
    against the refresh token whitelist so that revoked sessions stop being accepted
    immediately.

    Set ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK = False`` to skip that query and go back
    to fully stateless authentication, where revocation only takes effect once the access
    token expires.
    """


class JWTAllAuthDBAuthentication(SessionRevocationMixin, JWTAuthentication):
    """
    Same check as :class:`JWTAllAuthAuthentication`, on top of the simplejwt
    authentication class that loads the user from the database.
    """


def warn_if_revocation_is_not_enforced(rest_framework_settings) -> None:
    """
    Warn when the session check is enabled but no authentication class applies it.

    Called from the app config, after ``DEFAULT_AUTHENTICATION_CLASSES`` has been
    resolved. A project that swapped in simplejwt's own classes would silently keep
    honouring access tokens of revoked sessions.
    """
    if not session_check_enabled():
        return

    configured = rest_framework_settings.get('DEFAULT_AUTHENTICATION_CLASSES') or ()
    paths = [
        klass if isinstance(klass, str) else f'{klass.__module__}.{klass.__qualname__}'
        for klass in configured
    ]
    if any(path.startswith('jwt_allauth.') for path in paths):
        return
    if not any(path.startswith('rest_framework_simplejwt.') for path in paths):
        return

    warnings.warn(
        "jwt-allauth: DEFAULT_AUTHENTICATION_CLASSES uses simplejwt's authentication "
        "classes directly, so access tokens are not checked against the refresh token "
        "whitelist and revoked sessions stay usable until their access token expires. "
        "Use 'jwt_allauth.authentication.JWTAllAuthAuthentication' (or mix "
        "'jwt_allauth.authentication.SessionRevocationMixin' into your own class), or "
        f"set {SESSION_CHECK_SETTING} = False to silence this warning.",
        stacklevel=2,
    )
