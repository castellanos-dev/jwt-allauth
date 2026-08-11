from __future__ import annotations

import logging
from datetime import timedelta
from typing import NamedTuple, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone

from uuid import uuid4

from jwt_allauth.constants import (
    MFA_CHALLENGE_MAX_ATTEMPTS,
    MFA_LOCKOUT_SECONDS,
    MFA_SALT,
    MFA_TOKEN_MAX_AGE_SECONDS,
    MFA_PURPOSE_LOGIN_ATTEMPT,
    MFA_PURPOSE_LOGIN_CHALLENGE,
    MFA_PURPOSE_SETUP_CHALLENGE,
    MFA_PURPOSE_SETUP_SECRET,
    MFA_USER_MAX_ATTEMPTS,
)
from jwt_allauth.tokens.models import GenericTokenModel

logger = logging.getLogger(__name__)


def get_challenge_max_attempts() -> int:
    """Failed attempts tolerated on a single login challenge. ``0`` disables the limit."""
    return int(getattr(settings, "JWT_ALLAUTH_MFA_CHALLENGE_MAX_ATTEMPTS", MFA_CHALLENGE_MAX_ATTEMPTS))


def get_user_max_attempts() -> int:
    """Failed attempts tolerated per user within the lockout window. ``0`` disables the limit."""
    return int(getattr(settings, "JWT_ALLAUTH_MFA_MAX_ATTEMPTS", MFA_USER_MAX_ATTEMPTS))


def get_lockout_seconds() -> int:
    """Length of the sliding window used to count failed attempts and to lock a user out."""
    return int(getattr(settings, "JWT_ALLAUTH_MFA_LOCKOUT_SECONDS", MFA_LOCKOUT_SECONDS))


def _allauth_encrypt(text: str) -> str:
    try:
        from allauth.mfa.adapter import get_adapter
    except Exception:
        return text
    try:
        return get_adapter().encrypt(text)
    except Exception:
        return text


def _allauth_decrypt(text: str) -> str:
    try:
        from allauth.mfa.adapter import get_adapter
    except Exception:
        return text
    try:
        return get_adapter().decrypt(text)
    except Exception:
        return text


def _encrypt_secret(plaintext: str) -> str:
    """Encrypt a TOTP secret for storage."""
    signed = signing.dumps(plaintext, key=settings.SECRET_KEY, salt=MFA_SALT)
    return _allauth_encrypt(signed)


def _decrypt_secret(stored: str) -> str:
    """Decrypt a TOTP secret, falling back to plaintext for backward compatibility."""
    stored = _allauth_decrypt(stored)
    try:
        return signing.loads(stored, key=settings.SECRET_KEY, salt=MFA_SALT)
    except Exception:
        # Backward compatibility: pre-encryption secrets are stored as plaintext.
        logger.debug("Failed to decrypt TOTP secret; assuming legacy plaintext value.")
        if stored.startswith("gAAAAA"):
            return ""
        return stored


def _is_expired(created) -> bool:
    return created < timezone.now() - timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS)


def _purge_expired(user_id: int, purpose: str) -> None:
    """Drop the expired tokens of a user for a single purpose."""
    GenericTokenModel.objects.filter(
        user_id=user_id,
        purpose=purpose,
        created__lt=timezone.now() - timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS),
    ).delete()


def create_setup_challenge(user_id: int) -> str:
    # A challenge nobody completes is never read again, so it is only ever dropped here.
    _purge_expired(user_id, MFA_PURPOSE_SETUP_CHALLENGE)
    challenge_id = uuid4().hex
    GenericTokenModel.objects.create(
        user_id=user_id,
        token=challenge_id,
        purpose=MFA_PURPOSE_SETUP_CHALLENGE,
    )
    return challenge_id


def get_setup_challenge_user(setup_challenge_id: str):
    try:
        token_obj = GenericTokenModel.objects.filter(
            token=setup_challenge_id,
            purpose=MFA_PURPOSE_SETUP_CHALLENGE,
        ).latest("created")
    except GenericTokenModel.DoesNotExist:
        return None
    if _is_expired(token_obj.created):
        token_obj.delete()
        return None
    User = get_user_model()
    try:
        return User.objects.get(id=token_obj.user_id)
    except User.DoesNotExist:
        token_obj.delete()
        return None


def delete_setup_challenge(setup_challenge_id: str) -> None:
    GenericTokenModel.objects.filter(
        token=setup_challenge_id,
        purpose=MFA_PURPOSE_SETUP_CHALLENGE,
    ).delete()


def store_setup_secret(user_id: int, secret: str) -> None:
    GenericTokenModel.objects.filter(
        user_id=user_id,
        purpose=MFA_PURPOSE_SETUP_SECRET,
    ).delete()
    GenericTokenModel.objects.create(
        user_id=user_id,
        token=_encrypt_secret(secret),
        purpose=MFA_PURPOSE_SETUP_SECRET,
    )


def load_setup_secret(user_id: int) -> Optional[str]:
    try:
        token_obj = GenericTokenModel.objects.filter(
            user_id=user_id,
            purpose=MFA_PURPOSE_SETUP_SECRET,
        ).latest("created")
    except GenericTokenModel.DoesNotExist:
        return None
    if _is_expired(token_obj.created):
        token_obj.delete()
        return None
    return _decrypt_secret(token_obj.token)


def delete_setup_secret(user_id: int) -> None:
    GenericTokenModel.objects.filter(
        user_id=user_id,
        purpose=MFA_PURPOSE_SETUP_SECRET,
    ).delete()


def create_login_challenge(user_id: int) -> str:
    _purge_expired_attempts(user_id)
    _purge_expired(user_id, MFA_PURPOSE_LOGIN_CHALLENGE)
    challenge_id = uuid4().hex
    GenericTokenModel.objects.create(
        user_id=user_id,
        token=challenge_id,
        purpose=MFA_PURPOSE_LOGIN_CHALLENGE,
    )
    return challenge_id


def get_login_challenge_user(challenge_id: str):
    # Nothing constrains the column to a single row per challenge, so the newest match
    # is taken rather than letting a duplicate turn a rejection into a server error.
    try:
        token_obj = GenericTokenModel.objects.filter(
            token=challenge_id,
            purpose=MFA_PURPOSE_LOGIN_CHALLENGE,
        ).latest("created")
    except GenericTokenModel.DoesNotExist:
        return None
    if _is_expired(token_obj.created):
        token_obj.delete()
        return None
    return token_obj.user


def delete_login_challenge(challenge_id: str) -> None:
    """
    Invalidate a login challenge.

    Failed attempts recorded against the challenge are intentionally kept: they feed the
    per-user counter, which has to survive the challenge that produced them. Use
    :func:`clear_failed_login_attempts` to reset that counter.
    """
    GenericTokenModel.objects.filter(
        token=challenge_id,
        purpose=MFA_PURPOSE_LOGIN_CHALLENGE,
    ).delete()


def delete_user_login_challenges(user_id: int) -> None:
    """Invalidate every outstanding login challenge of a user."""
    GenericTokenModel.objects.filter(
        user_id=user_id,
        purpose=MFA_PURPOSE_LOGIN_CHALLENGE,
    ).delete()


class FailedAttemptResult(NamedTuple):
    """Outcome of recording a failed MFA verification."""

    #: The challenge used for the attempt is no longer usable.
    challenge_invalidated: bool
    #: The user exhausted the per-user budget; every challenge was dropped.
    locked_out: bool
    #: Seconds the user has to wait before the MFA step accepts codes again.
    retry_after: int


def _failed_attempts_qs(user_id: int):
    return GenericTokenModel.objects.filter(
        user_id=user_id,
        purpose=MFA_PURPOSE_LOGIN_ATTEMPT,
    )


def _purge_expired_attempts(user_id: int) -> None:
    """Drop attempts that no longer count towards any limit."""
    # Attempts are also the per-challenge counter, so never purge one that a live
    # challenge could still be counting.
    max_age = max(get_lockout_seconds(), MFA_TOKEN_MAX_AGE_SECONDS)
    _failed_attempts_qs(user_id).filter(
        created__lt=timezone.now() - timedelta(seconds=max_age)
    ).delete()


def clear_failed_login_attempts(user_id: int) -> None:
    """Reset the per-user attempt counter, e.g. after a successful verification."""
    _failed_attempts_qs(user_id).delete()


def login_lockout_remaining(user_id: int) -> int:
    """
    Return how many seconds the user is locked out of the MFA step, ``0`` when they are not.

    The window slides: the user is locked out for as long as the last
    ``JWT_ALLAUTH_MFA_MAX_ATTEMPTS`` failures all sit within
    ``JWT_ALLAUTH_MFA_LOCKOUT_SECONDS``, and is released as soon as the oldest of them
    ages out.
    """
    max_attempts = get_user_max_attempts()
    if max_attempts <= 0:
        return 0
    lockout_seconds = get_lockout_seconds()
    now = timezone.now()
    recent = list(
        _failed_attempts_qs(user_id)
        .filter(created__gte=now - timedelta(seconds=lockout_seconds))
        .order_by("-created")
        .values_list("created", flat=True)[:max_attempts]
    )
    if len(recent) < max_attempts:
        return 0
    remaining = (recent[-1] + timedelta(seconds=lockout_seconds) - now).total_seconds()
    return max(int(remaining), 1)


def is_login_locked_out(user_id: int) -> bool:
    return login_lockout_remaining(user_id) > 0


def record_failed_login_attempt(challenge_id: str, user) -> FailedAttemptResult:
    """
    Record a failed MFA verification and apply the per-challenge and per-user limits.

    The whole read-modify-write runs inside a transaction that first locks the user row,
    so concurrent verifications of the same user are serialized and cannot slip past the
    thresholds together.
    """
    with transaction.atomic():
        _lock_user(user.pk)
        _purge_expired_attempts(user.pk)
        GenericTokenModel.objects.create(
            user=user,
            token=challenge_id,
            purpose=MFA_PURPOSE_LOGIN_ATTEMPT,
        )

        retry_after = login_lockout_remaining(user.pk)
        if retry_after:
            # Requesting a new challenge must not buy the attacker more guesses, so drop
            # the ones already issued as well.
            delete_user_login_challenges(user.pk)
            return FailedAttemptResult(challenge_invalidated=True, locked_out=True, retry_after=retry_after)

        challenge_max_attempts = get_challenge_max_attempts()
        if challenge_max_attempts > 0:
            challenge_attempts = _failed_attempts_qs(user.pk).filter(token=challenge_id).count()
            if challenge_attempts >= challenge_max_attempts:
                delete_login_challenge(challenge_id)
                return FailedAttemptResult(challenge_invalidated=True, locked_out=False, retry_after=0)

        return FailedAttemptResult(challenge_invalidated=False, locked_out=False, retry_after=0)


def _lock_user(user_id: int) -> None:
    """
    Take a row lock on the user for the duration of the current transaction.

    On backends without ``SELECT ... FOR UPDATE`` support (e.g. SQLite, which serializes
    writers anyway) Django ignores the clause and this is a plain read.
    """
    list(get_user_model().objects.select_for_update().filter(pk=user_id).values_list("pk", flat=True))
