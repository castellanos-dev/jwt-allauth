"""
The social endpoints.

One view per flow serves every provider: the provider comes from the URL and is resolved
through allauth's registry, so a project adds Google or Apple by configuring it, not by
subclassing anything here.

The login views end where every other way in ends -- ``RefreshToken.for_user`` and
:func:`~jwt_allauth.utils.build_token_response` -- so a session opened through a provider
is a session like any other: on the whitelist, carrying its device, closable from
``/logout/`` and subject to rotation. Connecting and disconnecting deliberately do
neither: they are account management, not authentication.
"""

from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from allauth.socialaccount.models import SocialAccount
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from jwt_allauth.mfa.gate import mfa_challenge
# `extend_schema` is used here rather than in `jwt_allauth.schema` because the
# annotations below reference serializers that import allauth's socialaccount models,
# and that module is imported by every view of the library.
from jwt_allauth.schema import extend_schema, social_login_schema
from jwt_allauth.social.flows import (
    authenticate_social_login,
    connect_social_login,
    disconnect_social_account,
    get_provider,
    sociallogin_from_code,
    sociallogin_from_token,
)
from jwt_allauth.social.serializers import (
    SocialAccountSerializer,
    SocialCodeSerializer,
    SocialProviderSerializer,
    SocialTokenSerializer,
)
from jwt_allauth.throttling import ExtraThrottlesMixin
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.utils import (
    build_token_response,
    get_user_agent,
    load_user,
    sensitive_post_parameters_m,
)


class _CredentialMixin:
    # Schema generators describe an endpoint with the first docstring along the MRO, so
    # the mixins carry none. See `jwt_allauth.throttling`.
    __doc__ = None

    def read_credential(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class TokenCredentialMixin(_CredentialMixin):
    __doc__ = None

    serializer_class = SocialTokenSerializer
    build_sociallogin = staticmethod(sociallogin_from_token)


class CodeCredentialMixin(_CredentialMixin):
    __doc__ = None

    serializer_class = SocialCodeSerializer
    build_sociallogin = staticmethod(sociallogin_from_code)


class BaseSocialLoginView(ExtraThrottlesMixin, APIView):
    __doc__ = None

    permission_classes = (AllowAny,)
    extra_throttle_classes = (AnonRateThrottle,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @get_user_agent
    def post(self, request: Request, provider: str, *args, **kwargs) -> Response:
        data = self.read_credential(request)
        prov = get_provider(request, provider, data.get('client_id'))
        sociallogin = self.build_sociallogin(request, prov, data)
        user, email_verified = authenticate_social_login(request, sociallogin)

        # A provider is a way of proving the first factor, not a substitute for the
        # second: whoever takes over the identity provider account would otherwise walk
        # straight past the authenticator this account enrolled.
        challenge = mfa_challenge(user)
        if challenge is not None:
            return Response(challenge, status=status.HTTP_200_OK)

        return build_token_response(
            RefreshToken.for_user(user, request, email_verified=email_verified))


class BaseSocialConnectView(ExtraThrottlesMixin, APIView):
    __doc__ = None

    permission_classes = (IsAuthenticated,)
    extra_throttle_classes = (AnonRateThrottle, UserRateThrottle)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @load_user
    def post(self, request: Request, provider: str, *args, **kwargs) -> Response:
        data = self.read_credential(request)
        prov = get_provider(request, provider, data.get('client_id'))
        sociallogin = self.build_sociallogin(request, prov, data)
        account = connect_social_login(request, sociallogin, request.user)
        return Response(SocialAccountSerializer(account).data, status=status.HTTP_201_CREATED)


@social_login_schema
class SocialTokenLoginView(TokenCredentialMixin, BaseSocialLoginView):
    """
    Open a session from a credential issued by a provider.

    For clients that talk to the provider themselves -- a mobile SDK, Google's web
    library -- and hand over the resulting ``id_token`` or ``access_token``. The
    ``client_id`` the credential was issued for has to be sent alongside it: a bearer
    token minted for another application of the same provider is not proof of anything
    here.

    Answers with the access token in the body and the refresh token as an HttpOnly
    cookie, or with an MFA challenge when the account has a second factor.
    """


@social_login_schema
class SocialCodeLoginView(CodeCredentialMixin, BaseSocialLoginView):
    """
    Open a session from an authorization code.

    For browser clients: the code is exchanged with the provider server side, so the app
    secret never reaches the frontend. Send the ``callback_url`` used in the
    authorization request and, when the provider supports PKCE, the ``code_verifier``.
    """


@extend_schema(responses={201: SocialAccountSerializer})
class SocialTokenConnectView(TokenCredentialMixin, BaseSocialConnectView):
    """
    Connect a provider to the account already signed in, from a provider credential.

    No session is opened and none is closed: this is account management. The provider's
    addresses are not added to the account either.
    """


@extend_schema(responses={201: SocialAccountSerializer})
class SocialCodeConnectView(CodeCredentialMixin, BaseSocialConnectView):
    """
    Connect a provider to the account already signed in, from an authorization code.
    """


class SocialAccountListView(ExtraThrottlesMixin, ListAPIView):
    """
    The providers connected to the account signed in.
    """

    permission_classes = (IsAuthenticated,)
    extra_throttle_classes = (AnonRateThrottle, UserRateThrottle)
    serializer_class = SocialAccountSerializer
    pagination_class = None

    def get_queryset(self):
        return SocialAccount.objects.filter(user=self.request.user.id).order_by('id')


@extend_schema(responses={204: None})
class SocialAccountDisconnectView(ExtraThrottlesMixin, APIView):
    """
    Disconnect a provider from the account signed in.

    Refused when it is the only way into the account: an account created through a
    provider has no usable password, so removing its last connection would leave nothing
    to sign in with and nothing to reset.
    """

    permission_classes = (IsAuthenticated,)
    extra_throttle_classes = (AnonRateThrottle, UserRateThrottle)

    def delete(self, request: Request, pk: int, *args, **kwargs) -> Response:
        # Scoped to the caller before anything else: an id that belongs to somebody else
        # has to be indistinguishable from one that does not exist.
        # `select_related`: `validate_disconnect` reads `account.user.has_usable_password()`,
        # and the caller is a stateless `TokenUser` that cannot answer it.
        accounts = list(SocialAccount.objects.filter(user=request.user.id).select_related('user'))
        account = next((a for a in accounts if a.pk == pk), None)
        if account is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        disconnect_social_account(request, account, accounts)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses={200: SocialProviderSerializer(many=True)})
class SocialProviderListView(ExtraThrottlesMixin, APIView):
    """
    The providers this installation has configured.

    Lets a frontend render the buttons it should render, with the ``client_id`` each
    authorization request needs. The app secret is never part of it.
    """

    permission_classes = (AllowAny,)
    extra_throttle_classes = (AnonRateThrottle,)

    def get(self, request: Request, *args, **kwargs) -> Response:
        providers = [
            {
                'id': provider.id,
                'name': provider.name,
                'client_id': getattr(provider.app, 'client_id', None) if getattr(provider, 'app', None) else None,
            }
            for provider in get_social_adapter().list_providers(request)
        ]
        return Response(SocialProviderSerializer(providers, many=True).data)
