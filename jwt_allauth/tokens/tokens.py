import hashlib
from uuid import uuid4

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken as DefaultRefreshToken

from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE
from jwt_allauth.tokens.models import GenericTokenModel
from jwt_allauth.tokens.serializers import RefreshTokenWhitelistSerializer, GenericTokenModelSerializer
from jwt_allauth.utils import user_agent_dict


class RefreshToken(DefaultRefreshToken):

    def set_session(self, id_=None):
        """
        Unique identifier of the session associated to the refresh token.
        """
        if id_ is None:
            id_ = uuid4().hex
        self.payload['session'] = id_

    def set_user_role(self, user):
        if user.is_staff:
            self.payload['role'] = STAFF_CODE
        elif user.is_superuser:
            self.payload['role'] = SUPER_USER_CODE
        else:
            self.payload['role'] = user.role

    @classmethod
    def for_user(cls, user, request=None, enabled=True):
        """
        Return
        ------
        RefreshToken

        """
        token = super().for_user(user)
        token.set_session()  # type: ignore
        token.set_user_role(user)  # type: ignore
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
            if GenericTokenModel.objects.filter(token=hashed_token, purpose=self.purpose).count() == 0:
                return False
            GenericTokenModel.objects.filter(token=hashed_token, purpose=self.purpose).delete()
        return result
