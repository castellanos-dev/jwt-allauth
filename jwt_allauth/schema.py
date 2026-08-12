"""
OpenAPI annotations for the endpoints whose response is not their serializer.

Most of the endpoints of this library answer with something other than the serializer
they validate the request with: registration validates ``email``/``password1`` and
answers with a session, and the flows authenticated by a capability cookie are
authorized by a cookie and a CSRF header rather than by a bearer token. A schema derived
from the serializers alone therefore describes the request faithfully and the response
not at all -- a frontend reading it looks for the token in ``email``, and an integrator
looks for a bearer the capability endpoints reject.

The annotations are applied through `drf-spectacular
<https://drf-spectacular.readthedocs.io/>`_ when it is installed (``pip install
django-jwt-allauth[schema]``) and are inert otherwise, so it stays an optional
dependency: :func:`extend_schema` below degrades to a decorator that returns what it is
given.
"""

from rest_framework import serializers

from jwt_allauth.constants import PASS_RESET_COOKIE, REFRESH_TOKEN_COOKIE, SET_PASSWORD_COOKIE

try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension
    from drf_spectacular.utils import OpenApiParameter, extend_schema

    SCHEMA_ANNOTATIONS_AVAILABLE = True

    class _JWTAllAuthScheme(OpenApiAuthenticationExtension):
        """Describe the bearer token the authenticated endpoints expect.

        drf-spectacular matches its built-in schemes by exact class, so the
        authentication classes of this library resolve to nothing without this and the
        endpoints come out with no security requirement at all.
        """

        target_class = 'jwt_allauth.authentication.JWTAllAuthAuthentication'
        name = 'jwtAllauth'

        def get_security_definition(self, auto_schema):
            return {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}

    class _JWTAllAuthDBScheme(_JWTAllAuthScheme):
        target_class = 'jwt_allauth.authentication.JWTAllAuthDBAuthentication'

except ImportError:  # pragma: no cover - exercised by installations without the extra
    SCHEMA_ANNOTATIONS_AVAILABLE = False

    OpenApiParameter = None

    def extend_schema(*args, **kwargs):
        """No-op stand-in for ``drf_spectacular.utils.extend_schema``."""
        def decorator(obj):
            return obj
        return decorator


REFRESH_COOKIE_NOTE = (
    f'Delivered in the ``{REFRESH_TOKEN_COOKIE}`` HttpOnly cookie unless '
    f'``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``, in which case it is in this field.'
)


class SessionResponseSerializer(serializers.Serializer):
    """Response of the endpoints that open a session. Documentation only."""

    access = serializers.CharField(help_text='JWT access token.')
    refresh = serializers.CharField(required=False, help_text=REFRESH_COOKIE_NOTE)
    detail = serializers.CharField(required=False, help_text='Outcome of the operation.')


class PasswordChangeResponseSerializer(serializers.Serializer):
    """Response of ``POST /password/change/``. Documentation only."""

    detail = serializers.CharField(help_text='Outcome of the operation.')
    access = serializers.CharField(
        required=False,
        help_text=(
            'Access token of the session minted after the change. Absent with '
            '``LOGOUT_ON_PASSWORD_CHANGE = False``, where nothing is revoked and the caller '
            'keeps the session it came in with.'
        ),
    )
    refresh = serializers.CharField(required=False, help_text=REFRESH_COOKIE_NOTE)


class RegistrationResponseSerializer(serializers.Serializer):
    """Response of ``POST /registration/``. Documentation only."""

    access = serializers.CharField(
        required=False,
        help_text=(
            'JWT access token. Absent while e-mail verification is mandatory: the session '
            'is withheld until the address is confirmed.'
        ),
    )
    refresh = serializers.CharField(required=False, help_text=REFRESH_COOKIE_NOTE)
    detail = serializers.CharField(
        required=False,
        help_text='Present when a verification e-mail has been sent.',
    )
    mfa_setup_required = serializers.BooleanField(
        required=False,
        help_text='Present when ``JWT_ALLAUTH_MFA_TOTP_MODE = \'required\'``.',
    )
    setup_challenge_id = serializers.CharField(
        required=False,
        help_text='Challenge to bootstrap MFA enrolment with, alongside ``mfa_setup_required``.',
    )


def capability_parameters(cookie_name):
    """
    Declare how a capability endpoint is authorized: a cookie and a CSRF header.

    These endpoints declare no authentication class -- a bearer token is ignored there,
    and the permission behind them turns down a request that arrives already
    authenticated -- so nothing in a serializer-derived schema says what to send.

    Args:
        cookie_name (str): Name of the cookie holding the capability.

    Returns:
        list: ``OpenApiParameter`` instances, empty when drf-spectacular is not installed.
    """
    if not SCHEMA_ANNOTATIONS_AVAILABLE:
        return []
    return [
        OpenApiParameter(
            name=cookie_name,
            type=str,
            location=OpenApiParameter.COOKIE,
            required=True,
            description=(
                'One-time capability, set as an HttpOnly cookie on the redirect the e-mail '
                'link lands on. This endpoint authenticates from it alone: it takes no '
                'bearer token and rejects a request that carries one.'
            ),
        ),
        OpenApiParameter(
            name='X-CSRFToken',
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description=(
                'CSRF token, read from the ``csrftoken`` cookie set on the same redirect. '
                'Not required when ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF = False``.'
            ),
        ),
    ]


#: Annotation for ``POST /password/reset/set-new/``.
reset_password_schema = extend_schema(
    parameters=capability_parameters(PASS_RESET_COOKIE),
    responses={200: SessionResponseSerializer},
)

#: Annotation for ``POST /registration/set-password/``.
set_password_schema = extend_schema(
    parameters=capability_parameters(SET_PASSWORD_COOKIE),
    responses={200: SessionResponseSerializer},
)

#: Annotation for ``POST /registration/``.
registration_schema = extend_schema(responses={201: RegistrationResponseSerializer})

#: Annotation for ``POST /login/``.
login_schema = extend_schema(responses={200: SessionResponseSerializer})

#: Annotation for ``POST /refresh/``.
token_refresh_schema = extend_schema(responses={200: SessionResponseSerializer})

#: Annotation for ``POST /password/change/``.
password_change_schema = extend_schema(responses={200: PasswordChangeResponseSerializer})
