from __future__ import annotations

import base64
import hashlib
import logging
from datetime import timedelta
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken as FernetInvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from uuid import uuid4

from jwt_allauth.constants import (
    MFA_TOKEN_MAX_AGE_SECONDS,
    MFA_PURPOSE_LOGIN_ATTEMPT,
    MFA_PURPOSE_LOGIN_CHALLENGE,
    MFA_PURPOSE_SETUP_CHALLENGE,
    MFA_PURPOSE_SETUP_SECRET,
)
from jwt_allauth.tokens.models import GenericTokenModel

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the Django SECRET_KEY."""
    key_material = settings.SECRET_KEY.encode()
    digest = hashlib.sha256(key_material).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_secret(plaintext: str) -> str:
    """Encrypt a TOTP secret for storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def _decrypt_secret(stored: str) -> str:
    """Decrypt a TOTP secret, falling back to plaintext for backward compatibility."""
    try:
        return _get_fernet().decrypt(stored.encode()).decode()
    except (FernetInvalidToken, Exception):
        # Backward compatibility: pre-encryption secrets are stored as plaintext.
        logger.debug("Failed to decrypt TOTP secret; assuming legacy plaintext value.")
        return stored


def _is_expired(created) -> bool:
    return created < timezone.now() - timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS)


def create_setup_challenge(user_id: int) -> str:
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
    challenge_id = uuid4().hex
    GenericTokenModel.objects.create(
        user_id=user_id,
        token=challenge_id,
        purpose=MFA_PURPOSE_LOGIN_CHALLENGE,
    )
    return challenge_id


def get_login_challenge_user(challenge_id: str):
    try:
        token_obj = GenericTokenModel.objects.get(
            token=challenge_id,
            purpose=MFA_PURPOSE_LOGIN_CHALLENGE,
        )
    except GenericTokenModel.DoesNotExist:
        return None
    if _is_expired(token_obj.created):
        token_obj.delete()
        return None
    return token_obj.user


def delete_login_challenge(challenge_id: str) -> None:
    GenericTokenModel.objects.filter(
        token=challenge_id,
        purpose__in=[MFA_PURPOSE_LOGIN_CHALLENGE, MFA_PURPOSE_LOGIN_ATTEMPT],
    ).delete()
