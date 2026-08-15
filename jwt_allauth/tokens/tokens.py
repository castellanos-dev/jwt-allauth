import hashlib
from datetime import datetime
from typing import Optional
from django.conf import settings
from uuid import uuid4
from inspect import getattr_static

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken as DefaultRefreshToken
from rest_framework_simplejwt.utils import aware_utcnow, datetime_from_epoch, datetime_to_epoch

from jwt_allauth.constants import EMAIL_VERIFIED_CLAIM, SESSION_IAT_CLAIM
from jwt_allauth.roles import get_user_role
from jwt_allauth.tokens.models import GenericTokenModel
from jwt_allauth.tokens.serializers import RefreshTokenWhitelistSerializer, GenericTokenModelSerializer
from jwt_allauth.utils import get_session_lifetime, is_email_verified, user_agent_dict

# Claims managed by the token itself. They are never regenerated from the
# user attribute configuration.
RESERVED_CLAIMS = (
    'token_type', 'exp', 'iat', 'jti', 'user_id', 'session', SESSION_IAT_CLAIM, 'role', EMAIL_VERIFIED_CLAIM,
)


class RefreshToken(DefaultRefreshToken):

    def set_session(self, id_=None):
        """
        Unique identifier of the session associated to the refresh token.
        """
        if id_ is None:
            id_ = uuid4().hex
        self.payload['session'] = id_

    def set_session_iat(self, at_time: Optional[datetime] = None):
        """
        Timestamp at which the session started.

        Unlike ``iat``, this claim is carried over to every rotated refresh token, which
        makes it possible to enforce an absolute session lifetime.
        """
        self.set_iat(claim=SESSION_IAT_CLAIM, at_time=at_time)

    def session_deadline(self) -> Optional[datetime]:
        """
        Instant at which the session reaches its absolute lifetime, or ``None`` when the
        limit is disabled or the token carries no session start (e.g. one-time tokens).
        """
        lifetime = get_session_lifetime()
        if lifetime is None or SESSION_IAT_CLAIM not in self.payload:
            return None
        return datetime_from_epoch(self.payload[SESSION_IAT_CLAIM]) + lifetime

    def session_expired(self, at_time: Optional[datetime] = None) -> bool:
        """
        Whether the session has already reached its absolute lifetime.
        """
        deadline = self.session_deadline()
        if deadline is None:
            return False
        return deadline <= (at_time if at_time is not None else aware_utcnow())

    def cap_exp_to_session(self):
        """
        Shorten the ``exp`` claim so that the token never outlives the session deadline.
        """
        deadline = self.session_deadline()
        if deadline is not None and 'exp' in self.payload:
            self.payload['exp'] = min(self.payload['exp'], datetime_to_epoch(deadline))

    @property
    def access_token(self) -> AccessToken:
        """
        Access token derived from this refresh token, never outliving the session deadline.
        """
        access = super().access_token
        deadline = self.session_deadline()
        if deadline is not None:
            access.payload['exp'] = min(access.payload['exp'], datetime_to_epoch(deadline))
        return access

    @staticmethod
    def _attribute_map():
        """
        Return the configured mapping of claim name to dot-path on the user object.
        """
        configured_attributes = getattr(settings, 'JWT_ALLAUTH_USER_ATTRIBUTES', {})

        # Accept legacy list format for backward compatibility but prefer dict.
        # In legacy mode, the final attribute name is used as the claim key.
        if isinstance(configured_attributes, list):
            return {
                attr_path.split('.')[-1]: attr_path
                for attr_path in configured_attributes
            }
        if isinstance(configured_attributes, dict):
            return configured_attributes
        return {}

    def set_user_attributes(self, user):
        """
        Add configurable user attributes to the token payload.
        Expects settings.JWT_ALLAUTH_USER_ATTRIBUTES as a dict mapping
        output claim names to dot-paths on the user object.
        Example: {'organization_id': 'organization.id', 'area_id': 'area.id'}
        """
        attribute_map = self._attribute_map()

        # Validate configuration: output names must be unique and must not collide
        # with reserved payload keys like 'role'.
        output_names = list(attribute_map.keys())
        duplicates = sorted(set([name for name in output_names if output_names.count(name) > 1]))
        reserved_conflicts = []
        if 'role' in output_names:
            reserved_conflicts.append('role')
        if duplicates or reserved_conflicts:
            conflict_list = sorted(set(duplicates + reserved_conflicts))
            raise ValueError(
                f"Incompatible JWT_ALLAUTH_USER_ATTRIBUTES: duplicate or reserved attribute names {conflict_list}"
            )

        for output_name, attr_path in attribute_map.items():
            keys = attr_path.split('.')
            current_value = user
            missing = False

            for key in keys:
                # First, verify the attribute exists without triggering __getattr__
                try:
                    getattr_static(current_value, key)
                except AttributeError:
                    missing = True
                    break

                # Then, resolve the runtime value (to handle descriptors/properties)
                try:
                    current_value = getattr(current_value, key)
                except Exception:
                    missing = True
                    break

                if current_value is None:
                    missing = True
                    break

            if not missing and output_name != 'role' and output_name not in self.payload and not callable(current_value):
                self.payload[output_name] = current_value

    def set_user_role(self, user):
        """
        Record the role of the account.

        Where the number comes from is the user model's business, not this token's: a
        model carrying a ``role`` is authoritative, and one without it falls back to the
        staff flags. See :mod:`jwt_allauth.roles`.
        """
        self.payload['role'] = get_user_role(user)

    def set_email_verified(self, user, verified=None):
        """
        Record whether the account has a confirmed e-mail address.

        The claim only ever goes from ``False`` to ``True`` for a given address, so a
        token that has not been rotated since the confirmation denies access it should
        by now be granting -- never the other way round. The exception is an address
        changed after the fact, and that one is bounded by the life of the access token.

        Args:
            user (AbstractBaseUser): Owner of the token.
            verified (bool|None): The answer, when the caller has just asked the same
                question -- a login gate does, immediately before minting. ``None`` asks
                the database. Never cached on the user instance: an address confirmed
                earlier in the same request would make a cached answer wrong.
        """
        self.payload[EMAIL_VERIFIED_CLAIM] = is_email_verified(user) if verified is None else verified

    def sync_user_claims(self, user):
        """
        Re-read the role, the verification state and the configured user attributes
        from the database.

        Called on refresh token rotation so that privilege changes take effect on
        the next refresh instead of surviving until the refresh token expires. It is
        also what turns ``email_verified`` on: the frontend calls ``/refresh/`` once the
        user has followed the confirmation link and the next access token carries it.
        """
        for output_name in self._attribute_map():
            if output_name not in RESERVED_CLAIMS:
                self.payload.pop(output_name, None)
        self.set_user_role(user)
        self.set_email_verified(user)
        self.set_user_attributes(user)

    @classmethod
    def for_user(cls, user, request=None, enabled=True, email_verified=None):
        """
        Args:
            user (AbstractBaseUser): Account to open the session for.
            request (HttpRequest|None): Request the device is recorded from.
            enabled (bool): Whether the session may be refreshed straight away.
            email_verified (bool|None): Passed on to :meth:`set_email_verified` when the
                caller has already asked; ``None`` lets the token ask.

        Return
        ------
        RefreshToken

        """
        token = super().for_user(user)
        token.set_session()  # type: ignore
        token.set_session_iat()  # type: ignore
        token.cap_exp_to_session()  # type: ignore
        token.set_user_role(user)  # type: ignore
        if email_verified is None:
            # Called with one argument unless the caller actually has an answer, so a
            # subclass that overrode `set_email_verified(self, user)` -- the shape this
            # method had before -- keeps working on every path that does not.
            token.set_email_verified(user)  # type: ignore
        else:
            token.set_email_verified(user, email_verified)  # type: ignore
        token.set_user_attributes(user)  # type: ignore
        # Store the token in the database
        refresh_serializer = RefreshTokenWhitelistSerializer(data={
            'jti': token.payload['jti'],
            'user': user.id,
            'enabled': enabled,
            'session': token.payload['session'],
            **user_agent_dict(request)
        })
        try:
            refresh_serializer.is_valid(raise_exception=True)
            refresh_serializer.save()
        except ValidationError as e:
            raise InvalidToken(e.args[0])
        return token


class GenericToken(PasswordResetTokenGenerator):

    def __init__(self, purpose, request=None):
        super().__init__()
        self.request = request
        self.purpose = purpose

    def make_token(self, user):
        token = super().make_token(user)
        hashed_token = hashlib.sha256(str(token).encode()).hexdigest()
        token_serializer = GenericTokenModelSerializer(data={
            'token': hashed_token,
            'user': user.id,
            'purpose': self.purpose,
            **user_agent_dict(self.request)
        })
        try:
            token_serializer.is_valid(raise_exception=True)
            token_serializer.save()
            # remove existing tokens for the same purpose
            GenericTokenModel.objects.filter(user=user, purpose=self.purpose).exclude(token=hashed_token).delete()
        except ValidationError as e:
            raise InvalidToken(e.args[0])
        return token

    def check_token(self, user, token):
        result = super().check_token(user, token)
        if result:
            hashed_token = hashlib.sha256(str(token).encode()).hexdigest()
            # Single use: claiming the row atomically keeps two concurrent clicks on the
            # same link from both being honoured.
            return GenericTokenModel.consume(hashed_token, self.purpose)
        return result
