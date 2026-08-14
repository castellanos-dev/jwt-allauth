import logging
from uuid import uuid4

from allauth.account import app_settings as allauth_settings
from allauth.account.utils import complete_signup
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.http import HttpResponseNotFound

from jwt_allauth.tokens.models import TokenModel
from jwt_allauth.registration.app_settings import register_permission_classes
from jwt_allauth.app_settings import RegisterSerializer
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.permissions import RegisterUsersPermission
from jwt_allauth.throttling import ExtraThrottlesMixin
from jwt_allauth.registration.serializers import UserRegisterSerializer
from jwt_allauth.schema import registration_schema
from jwt_allauth.utils import (
    enumeration_prevented,
    get_user_agent,
    invitations_enabled,
    refresh_token_as_cookie,
    self_registration_enabled,
    sensitive_post_parameters_m,
    set_refresh_token_cookie,
    verification_is_mandatory,
)
from jwt_allauth.constants import MFA_TOTP_REQUIRED
from jwt_allauth.mfa.gate import get_mfa_totp_mode
from jwt_allauth.mfa.storage import create_setup_challenge

logger = logging.getLogger(__name__)


@registration_schema
class RegisterView(ExtraThrottlesMixin, CreateAPIView):
    """
    Register an account.

    Answers ``201``. What comes back depends on the verification method: with
    ``EMAIL_VERIFICATION = 'mandatory'`` only a ``detail`` notice, since the session is
    withheld until the address is confirmed; otherwise the access token in the body and
    the refresh token as an HttpOnly cookie (in the body when
    ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``).
    """
    serializer_class = RegisterSerializer
    permission_classes = register_permission_classes()
    extra_throttle_classes = (AnonRateThrottle,)
    token_model = TokenModel
    jwt_token = RefreshToken

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(RegisterView, self).dispatch(*args, **kwargs)

    @staticmethod
    def get_response_data(token):
        """
        Body of the ``201``; the refresh token appears here only when it travels in it.

        Under ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` -- the default -- the refresh token
        is delivered as an HttpOnly cookie by :meth:`create`, the way every other endpoint
        of the library delivers it. Sign-up is the one response a script always reads, so
        leaving the longest-lived credential in it put it in the hands of JavaScript and
        left the CSRF check on rotation guarding something already exposed.

        Args:
            token: Refresh token issued for the new account, or ``None`` when none was.

        Returns:
            dict: JSON body of the response.
        """
        # Only mandatory verification withholds the session. Under
        # ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` the confirmation mail goes out all
        # the same, but the account is usable right away and the response carries the
        # tokens, exactly as it does when verification is off.
        if verification_is_mandatory():
            # While the address conflict is hidden, no refresh token is handed out:
            # it could only ever be minted for an account that was really created,
            # and its very presence -- let alone the user id it carries -- would tell
            # the caller whether the address was free. The token is of no use until
            # the address is verified anyway; set ``ACCOUNT_PREVENT_ENUMERATION`` to
            # ``False`` to get it back.
            data = {"detail": _("Verification e-mail sent.")}
        else:
            # No access token until the address is confirmed, so this is the only branch
            # that carries one.
            data = {'access': str(token.access_token)}

        if token is not None and not refresh_token_as_cookie():
            data['refresh'] = str(token)
        return data

    @get_user_agent
    def create(self, request, *args, **kwargs):
        # Closed registration removes this endpoint. Adding invitations does not: they
        # are a second way in, not a replacement for this one.
        if not self_registration_enabled():
            return HttpResponseNotFound()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # Case 1: MFA REQUIRED mode -> perform_create returns a dict with challenge
        if isinstance(result, dict) and result.get("mfa_setup_required"):
            return Response(result, status=status.HTTP_201_CREATED, headers=headers)

        # Case 2: Normal flow -> result is the refresh token
        token = result
        response = Response(self.get_response_data(token),
                            status=status.HTTP_201_CREATED,
                            headers=headers)
        if token is not None and refresh_token_as_cookie():
            set_refresh_token_cookie(response, token)
        return response

    def perform_create(self, serializer):
        # `user` is None when the address is already in use and the conflict is being
        # hidden: nothing was created, but the response has to look the same.
        user = serializer.save(self.request)

        if user is not None:
            # Complete allauth signup flow (email verification, etc.)
            complete_signup(self.request._request, user,
                            allauth_settings.EMAIL_VERIFICATION,
                            None)

        # If MFA TOTP is REQUIRED, don't emit session tokens here.
        # Instead, create a setup_challenge like in login.
        if get_mfa_totp_mode() == MFA_TOTP_REQUIRED:
            # A challenge that leads nowhere keeps the response indistinguishable;
            # redeeming it fails exactly like redeeming an expired one.
            setup_challenge_id = create_setup_challenge(user.id) if user is not None else uuid4().hex

            data = {
                "mfa_setup_required": True,
                "setup_challenge_id": setup_challenge_id,
            }
            # Only mandatory verification leaves the caller waiting for a link before
            # the session is of any use; say so only then.
            if verification_is_mandatory():
                data["detail"] = _("Verification e-mail sent.")

            return data

        if user is None or enumeration_prevented():
            # See `get_response_data`: the refresh token is left out of the response
            # while address conflicts are hidden, so there is none to issue.
            return None

        # Normal behavior when MFA is not REQUIRED:
        refresh = self.jwt_token.for_user(
            user, self.request, enabled=not verification_is_mandatory())

        return refresh


class UserRegisterView(CreateAPIView):
    """
    Admin-managed registration endpoint.
    - Only accessible to users with admin role (see AdminPermission).
    - Does not issue tokens on creation.
    - Triggers email verification; user will set password after verifying.
    """
    serializer_class = UserRegisterSerializer
    permission_classes = (RegisterUsersPermission,)
    http_method_names = ['post', 'head', 'options']

    @staticmethod
    def get_response_data(_):
        return {}

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        if not invitations_enabled():
            return HttpResponseNotFound()
        return super(UserRegisterView, self).dispatch(*args, **kwargs)

    @get_user_agent
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(self.get_response_data(None), status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(self.request)
        return None
