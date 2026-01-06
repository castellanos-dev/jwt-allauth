import logging

from allauth.account import app_settings as allauth_settings
# from allauth.account.adapter import get_adapter
from allauth.account.utils import complete_signup
# from allauth.socialaccount import signals
# from allauth.socialaccount.adapter import get_adapter as get_social_adapter
# from allauth.socialaccount.models import SocialAccount
from django.utils.translation import gettext_lazy as _
from rest_framework import status
# from rest_framework.exceptions import NotFound
from rest_framework.generics import CreateAPIView  #, ListAPIView, GenericAPIView
# from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponseNotFound

# from jwt_allauth.login.views import LoginView
from jwt_allauth.tokens.models import TokenModel
from jwt_allauth.registration.app_settings import register_permission_classes
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.permissions import RegisterUsersPermission
from jwt_allauth.registration.serializers import (
    UserRegisterSerializer,
)
# from jwt_allauth.registration.serializers import (
#     SocialLoginSerializer, SocialAccountSerializer, SocialConnectSerializer)
from jwt_allauth.utils import get_user_agent, sensitive_post_parameters_m
from jwt_allauth.constants import (
    MFA_TOTP_REQUIRED,
)
from jwt_allauth import app_settings
from jwt_allauth.mfa.storage import create_setup_challenge
from jwt_allauth.models import PhoneAddress

logger = logging.getLogger(__name__)


class RegisterView(CreateAPIView):
    permission_classes = register_permission_classes()
    token_model = TokenModel
    jwt_token = RefreshToken

    def get_serializer_class(self):
        return app_settings.RegisterSerializer

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(RegisterView, self).dispatch(*args, **kwargs)

    @staticmethod
    def get_response_data(token):
        if app_settings.IDENTIFIER_VERIFICATION:
            authentication_method = app_settings.AUTHENTICATION_METHOD
            return {
                "detail": (
                    _("Verification SMS sent.")
                    if authentication_method == 'phone'
                    else _("Verification e-mail sent.")
                ),
                'refresh': str(token)
            }

        else:
            return {
                'refresh': str(token),
                'access': str(token.access_token)
            }

    @get_user_agent
    def create(self, request, *args, **kwargs):
        # If admin-managed registration is enabled, disable open registration endpoint
        if app_settings.ADMIN_MANAGED_REGISTRATION:
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
        user = serializer.save(self.request)

        authentication_method = app_settings.AUTHENTICATION_METHOD

        if authentication_method == 'phone':
            # For phone-based identification, mirror the email flow:
            # if verification is enabled, issue an SMS confirmation.
            if app_settings.IDENTIFIER_VERIFICATION:
                phone_address = PhoneAddress.objects.filter(user=user).first()
                if phone_address is not None and not phone_address.verified:
                    phone_address.send_confirmation(self.request)
        else:
            # Complete allauth signup flow (email verification, etc.)
            complete_signup(self.request._request, user,
                            allauth_settings.EMAIL_VERIFICATION,
                            None)

        # If MFA TOTP is REQUIRED, don't emit session tokens here.
        # Instead, create a setup_challenge like in login.
        if app_settings.MFA_TOTP_MODE == MFA_TOTP_REQUIRED:
            setup_challenge_id = create_setup_challenge(user.id)

            data = {
                "mfa_setup_required": True,
                "setup_challenge_id": setup_challenge_id,
            }
            # If email verification is enabled, include the informative message
            if app_settings.IDENTIFIER_VERIFICATION:
                data["detail"] = (
                    _("Verification SMS sent.") if authentication_method == 'phone'
                    else _("Verification e-mail sent.")
                )

            return data

        # Normal behavior when MFA is not REQUIRED:
        refresh = self.jwt_token.for_user(
            user, self.request, enabled=not bool(app_settings.IDENTIFIER_VERIFICATION))

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
        if not app_settings.ADMIN_MANAGED_REGISTRATION:
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
