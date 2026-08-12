import logging
from uuid import uuid4

from allauth.account import app_settings as allauth_settings
# from allauth.account.adapter import get_adapter
from allauth.account.utils import complete_signup
# from allauth.socialaccount import signals
# from allauth.socialaccount.adapter import get_adapter as get_social_adapter
# from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
# from rest_framework.exceptions import NotFound
from rest_framework.generics import CreateAPIView  #, ListAPIView, GenericAPIView
# from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.http import HttpResponseNotFound

# from jwt_allauth.login.views import LoginView
from jwt_allauth.tokens.models import TokenModel
from jwt_allauth.registration.app_settings import register_permission_classes
from jwt_allauth.app_settings import RegisterSerializer
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.permissions import RegisterUsersPermission
from jwt_allauth.registration.serializers import UserRegisterSerializer
# from jwt_allauth.registration.serializers import (
#     SocialLoginSerializer, SocialAccountSerializer, SocialConnectSerializer)
from jwt_allauth.utils import (
    enumeration_prevented,
    get_user_agent,
    sensitive_post_parameters_m,
    verification_is_mandatory,
)
from jwt_allauth.constants import (
    MFA_TOTP_DISABLED,
    MFA_TOTP_REQUIRED,
)
from jwt_allauth.mfa.storage import create_setup_challenge

logger = logging.getLogger(__name__)


def get_mfa_totp_mode() -> str:
    """
    Return the current MFA TOTP mode from settings.

    This must be evaluated at call time (not import time) so that
    Django's `override_settings` used in tests – and any runtime changes
    – are respected.
    """
    return getattr(settings, "JWT_ALLAUTH_MFA_TOTP_MODE", MFA_TOTP_DISABLED)


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = register_permission_classes()
    throttle_classes = [AnonRateThrottle]
    token_model = TokenModel
    jwt_token = RefreshToken

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(RegisterView, self).dispatch(*args, **kwargs)

    @staticmethod
    def get_response_data(token):
        # Only mandatory verification withholds the session. Under
        # ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` the confirmation mail goes out all
        # the same, but the account is usable right away and the response carries the
        # tokens, exactly as it does when verification is off.
        if verification_is_mandatory():
            data = {"detail": _("Verification e-mail sent.")}
            # While the address conflict is hidden, no refresh token is handed out:
            # it could only ever be minted for an account that was really created,
            # and its very presence -- let alone the user id it carries -- would tell
            # the caller whether the address was free. The token is of no use until
            # the address is verified anyway; set ``ACCOUNT_PREVENT_ENUMERATION`` to
            # ``False`` to get it back.
            if token is not None:
                data['refresh'] = str(token)
            return data

        else:
            return {
                'refresh': str(token),
                'access': str(token.access_token)
            }

    @get_user_agent
    def create(self, request, *args, **kwargs):
        # If admin-managed registration is enabled, disable open registration endpoint
        if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
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
        return Response(self.get_response_data(token),
                        status=status.HTTP_201_CREATED,
                        headers=headers)

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
        if not getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
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


# class SocialLoginView(LoginView):
#     """
#     class used for social authentications
#     example usage for facebook with access_token
#     -------------
#     from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
#
#     class FacebookLogin(SocialLoginView):
#         adapter_class = FacebookOAuth2Adapter
#     -------------
#
#     example usage for facebook with code
#
#     -------------
#     from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
#     from allauth.socialaccount.providers.oauth2.client import OAuth2Client
#
#     class FacebookLogin(SocialLoginView):
#         adapter_class = FacebookOAuth2Adapter
#         client_class = OAuth2Client
#         callback_url = 'localhost:8000'
#     -------------
#     """
#     serializer_class = SocialLoginSerializer
#
#     def process_login(self):
#         get_adapter(self.request).login(self.request, self.user)
#
#
# class SocialConnectView(LoginView):
#     """
#     class used for social account linking
#
#     example usage for facebook with access_token
#     -------------
#     from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
#
#     class FacebookConnect(SocialConnectView):
#         adapter_class = FacebookOAuth2Adapter
#     -------------
#     """
#     serializer_class = SocialConnectSerializer
#     permission_classes = (IsAuthenticated,)
#
#     def process_login(self):
#         get_adapter(self.request).login(self.request, self.user)
#
#
# class SocialAccountListView(ListAPIView):
#     """
#     List SocialAccounts for the currently logged in user
#     """
#     serializer_class = SocialAccountSerializer
#     permission_classes = (IsAuthenticated,)
#
#     def get_queryset(self):
#         return SocialAccount.objects.filter(user=self.request.user)
#
#
# class SocialAccountDisconnectView(GenericAPIView):
#     """
#     Disconnect SocialAccount from remote service for
#     the currently logged in user
#     """
#     serializer_class = SocialConnectSerializer
#     permission_classes = (IsAuthenticated,)
#
#     def get_queryset(self):
#         return SocialAccount.objects.filter(user=self.request.user)
#
#     def post(self, request, *args, **kwargs):
#         accounts = self.get_queryset()
#         account = accounts.filter(pk=kwargs['pk']).first()
#         if not account:
#             raise NotFound
#
#         get_social_adapter(self.request).validate_disconnect(account, accounts)
#
#         account.delete()
#         signals.social_account_removed.send(
#             sender=SocialAccount,
#             request=self.request,
#             socialaccount=account
#         )
#
#         return Response(self.get_serializer(account).data)
