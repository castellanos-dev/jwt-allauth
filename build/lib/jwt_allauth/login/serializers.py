from typing import Dict, Any

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from jwt_allauth.token.app_settings import RefreshToken
from jwt_allauth.utils import allauth_authenticate


class LoginSerializer(TokenObtainPairSerializer):
    token_class = RefreshToken
    username_field = getattr(settings, 'ACCOUNT_AUTHENTICATION_METHOD', 'email')
    user = None

    @classmethod
    def get_token(cls, user) -> RefreshToken:
        """
        Instantiates a new TokenObtainPairSerializer object, sets a token for the given user and returns the token.
        """
        cls.token = cls.token_class.for_user(user)
        return cls.token  # type: ignore

    @transaction.atomic
    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        # Get the email and password information
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        # User authentication (allauth)
        self.user = allauth_authenticate(**authenticate_kwargs)

        # Active account check
        if not api_settings.USER_AUTHENTICATION_RULE(self.user):
            raise exceptions.AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )
        validated_data = super().validate(attrs)

        # Set the refresh token
        refresh = self.get_token(self.user)

        validated_data["refresh"] = str(refresh)
        validated_data["access"] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return validated_data
