"""
Settings that govern the social endpoints.

All of them are read at call time rather than at import, so that ``override_settings``
in a test -- and any change made after startup -- is honoured. This is the newer of the
two conventions in the codebase and the one :mod:`jwt_allauth.utils` follows.
"""

from typing import Optional, Sequence

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def email_linking_enabled(provider_id: str) -> bool:
    """
    Whether a provider may be linked to an account found by e-mail address.

    ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING`` takes ``True`` (the default), ``False``, or a
    list of provider ids. The list exists because the trust is not in the mechanism but
    in the provider: an installation can accept that Google has checked the mailbox
    behind ``email_verified`` and decline to accept the same claim from somewhere else.

    Args:
        provider_id (str): Id of the provider presenting the credential.

    Returns:
        bool: ``True`` when an address this provider vouches for may resolve to an
        account that already exists.
    """
    configured = getattr(settings, 'JWT_ALLAUTH_SOCIAL_EMAIL_LINKING', True)
    if isinstance(configured, bool):
        return configured
    if isinstance(configured, (list, tuple, set, frozenset)):
        return provider_id in configured
    raise ImproperlyConfigured(
        "jwt-allauth: JWT_ALLAUTH_SOCIAL_EMAIL_LINKING must be a bool or a list of provider ids."
    )


def require_verified_email() -> bool:
    """
    Whether a provider has to vouch for the address before an account is created.

    On by default. An account in this library is identified by its address, so one that
    nobody has vouched for is a dead end: there is no password to reset it with and no
    confirmation link worth sending to it. Turning it off falls back to the registration
    behaviour -- the session is withheld and a confirmation mail goes out.
    """
    return bool(getattr(settings, 'JWT_ALLAUTH_SOCIAL_REQUIRE_VERIFIED_EMAIL', True))


def allowed_callback_urls() -> Optional[Sequence[str]]:
    """
    Redirect URIs the authorization-code endpoint will exchange a code against.

    ``None`` (the default) accepts whatever the caller sends and leaves the decision to
    the provider, which rejects a ``redirect_uri`` that does not match the one the code
    was issued for. Setting it is defence in depth for an installation whose provider
    registration is broader than it should be.
    """
    configured = getattr(settings, 'JWT_ALLAUTH_SOCIAL_CALLBACK_URLS', None)
    if configured is None:
        return None
    if isinstance(configured, (list, tuple)):
        return tuple(configured)
    raise ImproperlyConfigured(
        "jwt-allauth: JWT_ALLAUTH_SOCIAL_CALLBACK_URLS must be a list of URLs or None."
    )


def callback_url_allowed(url: str) -> bool:
    """
    Whether ``url`` may be presented as the ``redirect_uri`` of a code exchange.

    Args:
        url (str): Address the caller says it used in the authorization request.

    Returns:
        bool: ``True`` when no allow-list is configured, or when ``url`` matches one of
        its entries exactly.
    """
    allowed = allowed_callback_urls()
    if allowed is None:
        return True
    return url in allowed
