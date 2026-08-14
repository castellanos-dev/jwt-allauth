"""
The step that stands between a proven credential and a session.

Authenticating is not the same as being let in: when the account carries a second
factor, whatever proved the first one -- a password, an identity provider -- buys a
challenge rather than a token. That decision is identical for every way into the
library, so it lives here instead of in each of them, and the endpoints that mint
sessions ask this module the same question.
"""

from typing import Any, Dict, Optional

from django.conf import settings
from rest_framework import exceptions

from jwt_allauth.constants import (
    MFA_TOTP_DISABLED,
    MFA_TOTP_REQUIRED,
)
from jwt_allauth.mfa.storage import (
    create_login_challenge,
    create_setup_challenge,
    login_lockout_remaining,
)


def get_mfa_totp_mode() -> str:
    """
    Return the current MFA TOTP mode from settings.

    This must be evaluated at call time (not import time) so that
    Django's `override_settings` used in tests – and any runtime changes
    – are respected.
    """
    return getattr(settings, "JWT_ALLAUTH_MFA_TOTP_MODE", MFA_TOTP_DISABLED)


try:
    from allauth.mfa.models import Authenticator  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    Authenticator = None  # type: ignore
    if get_mfa_totp_mode() != MFA_TOTP_DISABLED:
        raise Exception(
            "MFA TOTP is not available. Please ensure 'django-jwt-allauth[mfa]' "
            "is installed and 'allauth.mfa' is added to INSTALLED_APPS."
        )


def has_totp(user) -> bool:
    """
    Whether the account has a TOTP authenticator on file.

    Args:
        user: Account that has just proved its first factor.

    Returns:
        bool: ``False`` when MFA is unavailable, so that a missing optional dependency
        reads as "no second factor" rather than raising on every login.
    """
    if Authenticator is None:
        return False
    return Authenticator.objects.filter(
        user=user,
        type=getattr(Authenticator, "Type").TOTP if hasattr(Authenticator, "Type") else "totp",
    ).exists()


def mfa_challenge(user) -> Optional[Dict[str, Any]]:
    """
    The payload that has to precede the session, or ``None`` when nothing does.

    Returns ``{"mfa_setup_required": True, "setup_challenge_id": ...}`` under
    ``MFA_TOTP_REQUIRED`` for an account with no authenticator -- enrolment is
    bootstrapped rather than refused, so that turning the mode on does not lock out
    everybody who has not enrolled yet -- and
    ``{"mfa_required": True, "challenge_id": ...}`` for an account that has one.

    Args:
        user: Account whose first factor has just been proved.

    Returns:
        dict|None: Body to answer with instead of the tokens, or ``None`` when the
        caller may proceed to mint a session.

    Raises:
        rest_framework.exceptions.Throttled: While the account is locked out. Handing
            out a new challenge would hand out a fresh batch of code guesses with it.
    """
    mode = get_mfa_totp_mode()
    if mode == MFA_TOTP_DISABLED or Authenticator is None:
        return None

    if not has_totp(user):
        if mode == MFA_TOTP_REQUIRED:
            return {
                "mfa_setup_required": True,
                "setup_challenge_id": create_setup_challenge(user.id),
            }
        return None

    retry_after = login_lockout_remaining(user.id)
    if retry_after:
        raise exceptions.Throttled(
            wait=retry_after,
            detail="Too many failed MFA attempts. Try again later.",
        )

    return {"mfa_required": True, "challenge_id": create_login_challenge(user.id)}
