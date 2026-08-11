"""
Retention of the rows behind the tokens the library stores.

``GenericTokenModel`` backs every short-lived credential: password reset and password set
links, the capabilities they are exchanged for, email confirmations and the MFA
challenges, secrets and failed attempts. ``RefreshTokenWhitelistModel`` backs the
sessions. A row of either is dropped when the token it stands for is used, but nothing
uses the ones the user never comes back for — an unopened reset link, an invitation nobody
accepts, an MFA challenge abandoned at the code prompt, a session left behind on a device
that never logs out — so both tables only grow.

Those rows are worthless past the lifetime of the token they stand for: every flow checks
that lifetime before honouring a row, so deleting them changes no outcome. :func:`purge`
removes the single-use tokens and :func:`purge_sessions` the whitelisted refresh tokens;
the ``jwt_allauth_purge_tokens`` management command runs both.

Purposes the library does not know about are left alone: an application storing its own
tokens in this table decides their lifetime, and can declare it through
``JWT_ALLAUTH_TOKEN_RETENTION``::

    JWT_ALLAUTH_TOKEN_RETENTION = {'MY_PURPOSE': timedelta(hours=6)}

The same setting overrides the built-in retentions.
"""

from datetime import timedelta
from typing import Dict

from allauth.account import app_settings as allauth_app_settings
from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from jwt_allauth.constants import (
    EMAIL_CONFIRMATION,
    MFA_LOCKOUT_SECONDS,
    MFA_PURPOSE_LOGIN_ATTEMPT,
    MFA_PURPOSE_LOGIN_CHALLENGE,
    MFA_PURPOSE_SETUP_CHALLENGE,
    MFA_PURPOSE_SETUP_SECRET,
    MFA_TOKEN_MAX_AGE_SECONDS,
    PASS_RESET,
    PASS_RESET_ACCESS,
    PASS_SET,
    PASS_SET_ACCESS,
)
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel

#: Name of the setting extending or overriding the retentions below.
TOKEN_RETENTION_SETTING = 'JWT_ALLAUTH_TOKEN_RETENTION'


def _jwt_lifetime(name: str) -> timedelta:
    """
    Lifetime configured for a kind of JWT, read at call time.

    ``SIMPLE_JWT`` is filled in with the resolved defaults when the app starts, so it is
    the authoritative source and the one that follows ``override_settings``;
    ``api_settings`` covers a project that dropped the key from the dictionary.

    Args:
        name (str): ``SIMPLE_JWT`` key, e.g. ``'ACCESS_TOKEN_LIFETIME'``.

    Returns:
        timedelta: The configured lifetime.
    """
    configured = getattr(settings, 'SIMPLE_JWT', {}).get(name)
    return configured if configured is not None else getattr(jwt_settings, name)


def retentions() -> Dict[str, timedelta]:
    """
    How long a row of each known purpose stays relevant.

    Every value mirrors the expiry the flow that reads the row enforces on its own, so a
    row older than this can never be honoured again.

    Returns:
        dict: Mapping of purpose to the age past which its rows are useless.
    """
    # Reset and set links are signed by ``PasswordResetTokenGenerator``, which measures
    # their age against PASSWORD_RESET_TIMEOUT.
    reset_link = timedelta(seconds=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 60 * 60 * 24 * 3))
    # The capabilities those links are exchanged for are access tokens, checked against
    # their own ``exp``.
    capability = _jwt_lifetime('ACCESS_TOKEN_LIFETIME')
    # Confirmations are rejected past allauth's window by the verification view.
    confirmation = timedelta(days=allauth_app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS)
    # MFA challenges and setup secrets expire with MFA_TOKEN_MAX_AGE_SECONDS. Failed
    # attempts double as the per-user counter, so they have to outlive the lockout window.
    mfa_token = timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS)
    mfa_attempt = timedelta(
        seconds=max(
            int(getattr(settings, 'JWT_ALLAUTH_MFA_LOCKOUT_SECONDS', MFA_LOCKOUT_SECONDS)),
            MFA_TOKEN_MAX_AGE_SECONDS,
        )
    )

    known = {
        PASS_RESET: reset_link,
        PASS_SET: reset_link,
        PASS_RESET_ACCESS: capability,
        PASS_SET_ACCESS: capability,
        EMAIL_CONFIRMATION: confirmation,
        MFA_PURPOSE_SETUP_CHALLENGE: mfa_token,
        MFA_PURPOSE_LOGIN_CHALLENGE: mfa_token,
        MFA_PURPOSE_SETUP_SECRET: mfa_token,
        MFA_PURPOSE_LOGIN_ATTEMPT: mfa_attempt,
    }
    known.update(getattr(settings, TOKEN_RETENTION_SETTING, {}) or {})
    return known


def expired(purpose: str, retention: timedelta, now=None):
    """
    Queryset of the rows of ``purpose`` that are past ``retention``.

    Args:
        purpose (str): Purpose the rows were stored under.
        retention (timedelta): Age past which a row is useless.
        now (datetime, optional): Instant the age is measured from. Defaults to now.

    Returns:
        QuerySet: The rows that can be deleted.
    """
    now = now or timezone.now()
    return GenericTokenModel.objects.filter(purpose=purpose, created__lt=now - retention)


def purge(dry_run: bool = False, now=None) -> Dict[str, int]:
    """
    Delete every stored token that is past the retention of its purpose.

    Args:
        dry_run (bool): Count the rows without deleting them.
        now (datetime, optional): Instant the age is measured from. Defaults to now.

    Returns:
        dict: Number of rows removed (or that would be), keyed by purpose. Purposes with
        nothing to remove are left out.
    """
    now = now or timezone.now()
    removed: Dict[str, int] = {}
    for purpose, retention in retentions().items():
        query_set = expired(purpose, retention, now=now)
        count = query_set.count() if dry_run else query_set.delete()[0]
        if count:
            removed[purpose] = count
    return removed


def session_retention() -> timedelta:
    """
    Age past which a whitelisted refresh token can no longer be presented.

    A row is created when a refresh token is minted and removed when that token is
    rotated, revoked or logged out, so what is left past the lifetime of the token is a
    session nobody came back to. The refresh token is rejected on its own ``exp`` before
    the whitelist is even read, so the row can no longer decide anything: neither a
    rotation nor the reuse detection behind it.

    ``ACCESS_TOKEN_LIFETIME`` is taken into account as well because the row is also what
    ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`` matches an access token against. Access
    tokens are far shorter lived than refresh tokens, so this only guards against a
    configuration where they are not.

    Returns:
        timedelta: Age past which a whitelist row is useless.
    """
    return max(_jwt_lifetime('REFRESH_TOKEN_LIFETIME'), _jwt_lifetime('ACCESS_TOKEN_LIFETIME'))


def expired_sessions(now=None):
    """
    Queryset of the whitelisted refresh tokens that can no longer be presented.

    Args:
        now (datetime, optional): Instant the age is measured from. Defaults to now.

    Returns:
        QuerySet: The rows that can be deleted.
    """
    now = now or timezone.now()
    return RefreshTokenWhitelistModel.objects.filter(created__lt=now - session_retention())


def purge_sessions(dry_run: bool = False, now=None) -> int:
    """
    Delete every whitelisted refresh token that has expired.

    Args:
        dry_run (bool): Count the rows without deleting them.
        now (datetime, optional): Instant the age is measured from. Defaults to now.

    Returns:
        int: Number of rows removed, or that would be.
    """
    query_set = expired_sessions(now=now)
    return query_set.count() if dry_run else query_set.delete()[0]


def unknown_purposes() -> Dict[str, int]:
    """
    Stored purposes with no retention, and how many rows each of them holds.

    They are never purged; the count is reported so that a growing one does not go
    unnoticed.

    Returns:
        dict: Number of rows per unmanaged purpose.
    """
    counts = (
        GenericTokenModel.objects.exclude(purpose__in=set(retentions()))
        .values_list('purpose')
        .order_by()
        .annotate(total=Count('id'))
    )
    return {purpose: total for purpose, total in counts}
