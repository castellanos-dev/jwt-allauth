from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from uuid import uuid4

from jwt_allauth.constants import (
    MFA_TOKEN_MAX_AGE_SECONDS,
    MFA_PURPOSE_LOGIN_CHALLENGE,
    MFA_PURPOSE_SETUP_CHALLENGE,
    MFA_PURPOSE_SETUP_SECRET,
)
from jwt_allauth.tokens.models import GenericTokenModel


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
        token=secret,
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
    return token_obj.token


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
        purpose=MFA_PURPOSE_LOGIN_CHALLENGE,
    ).delete()
