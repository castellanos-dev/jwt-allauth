import uuid

from allauth.core.ratelimit import consume as consume_ratelimit
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, Throttled
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.app_settings import PasswordResetSerializer
from jwt_allauth.constants import (
    PASS_RESET, PASSWORD_RESET_REDIRECT, FOR_USER,
    ONE_TIME_PERMISSION, PASS_SET_ACCESS, PASS_RESET_ACCESS, PASS_RESET_COOKIE,
    SET_PASSWORD_COOKIE,
    MFA_TOKEN_MAX_AGE_SECONDS,
    MFA_TOTP_DISABLED,
    MFA_TOTP_REQUIRED,
    EMAIL_CONFIRMATION,
    INVITATION,
)
from jwt_allauth.password_reset.permissions import ResetPasswordPermission, SetPasswordPermission
from jwt_allauth.password_reset.serializers import SetPasswordSerializer
from jwt_allauth.schema import reset_password_schema, set_password_schema
from jwt_allauth.revocation import revoke_on_credential_change
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel
from jwt_allauth.tokens.serializers import GenericTokenModelSerializer
from jwt_allauth.throttling import ExtraThrottlesMixin
from jwt_allauth.tokens.tokens import GenericToken
from jwt_allauth.utils import (
    build_token_response,
    get_user_agent,
    invitations_enabled,
    load_capability_user,
    sensitive_post_parameters_m,
)
from jwt_allauth.csrf import ensure_csrf_cookie
from jwt_allauth.mfa.storage import create_setup_challenge


def get_mfa_totp_mode() -> str:
    """
    Return the current MFA TOTP mode from settings.

    This must be evaluated at call time (not import time) so that
    Django's `override_settings` used in tests – and any runtime changes
    – are respected.
    """
    return getattr(settings, "JWT_ALLAUTH_MFA_TOTP_MODE", MFA_TOTP_DISABLED)


class CapabilityCookieViewMixin:
    """
    Shared wiring for the endpoints authorized by a one-time capability cookie.

    No authentication class runs on them. Authorization is the cookie, and the permission
    behind it turns down a request that arrives already authenticated, since it replaces
    ``request.user`` with the holder of the capability: a native client that attaches its
    bearer token to every request would be locked out of the flow. A stale or malformed
    header is worse still -- the authentication class rejects it before the cookie is ever
    looked at.

    Without an authenticator declared, DRF reports a denied permission as ``403`` and
    degrades a ``401`` into one, since it has no scheme to challenge with. The cookie is a
    credential, so a missing or spent one keeps answering ``401`` the way it always has;
    the scheme named in ``WWW-Authenticate`` is the cookie itself. A failed CSRF check
    raises on its own and stays a ``403``.
    """
    authentication_classes = ()
    authenticate_header = 'Cookie'

    def permission_denied(self, request, message=None, code=None):
        raise NotAuthenticated(detail=message, code=code)

    def get_authenticate_header(self, request):
        return self.authenticate_header


class PasswordResetView(ExtraThrottlesMixin, GenericAPIView):
    """
    Calls Django Auth PasswordResetForm save method.

    Accepts the following POST parameters: email
    Returns the success/fail message.
    """
    serializer_class = PasswordResetSerializer
    permission_classes = (AllowAny,)
    extra_throttle_classes = (AnonRateThrottle,)

    @get_user_agent
    def post(self, request):
        # Create a serializer with request.data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # The throttle above counts requests per address of origin, which does not
        # protect the mailbox on the other end: rotating the origin is enough to keep a
        # victim's inbox under a stream of reset links. allauth's own ``reset_password``
        # limit is consumed here as well, keyed by the address being targeted (``5/m/key``
        # by default, alongside its ``20/m/ip``). It is consumed before the account is
        # looked up, so an address that is not registered answers exactly like one that
        # is. Set ``ACCOUNT_RATE_LIMITS = {'reset_password': None}`` to lift it.
        if not consume_ratelimit(
            request=getattr(request, '_request', request),
            action='reset_password',
            key=serializer.validated_data['email'],
        ):
            raise Throttled(detail=_('Too many password reset requests for this e-mail address.'))

        serializer.save()
        # Return the success message with OK HTTP status
        return Response(
            {"detail": _("Password reset e-mail has been sent.")},
            status=status.HTTP_200_OK
        )


class DefaultPasswordResetView(GenericAPIView):
    """
    Default view for password reset form.
    """
    permission_classes = (AllowAny,)
    template_name = 'password/reset.html'

    def get(self, request):
        return render(request, self.template_name, {
            'validlink': PASS_RESET_COOKIE in request.COOKIES,
            'form': None
        })


class DefaultSetPasswordView(GenericAPIView):
    """
    Default view for admin-managed registration password set form.

    This renders a minimal HTML UI that posts to the API-based SetPasswordView
    (rest_set_password) and relies on the SET_PASSWORD_COOKIE for authorization.
    """
    permission_classes = (AllowAny,)
    template_name = 'password/set.html'

    def get(self, request):
        return render(request, self.template_name, {
            'validlink': SET_PASSWORD_COOKIE in request.COOKIES,
        })


class PasswordResetConfirmView(GenericAPIView):
    """
    Validates the password reset link and hands over a one-time reset cookie.

    This endpoint is reached by anonymous users clicking the link sent by
    email, so it must stay public regardless of the project's
    ``DEFAULT_PERMISSION_CLASSES``. It authenticates nobody either: a stale or
    malformed ``Authorization`` header that a native client attaches to every request
    would otherwise answer ``401`` to a link that carries its own credential.
    """
    authentication_classes = ()
    permission_classes = (AllowAny,)
    form_url = getattr(settings, PASSWORD_RESET_REDIRECT, None)

    @get_user_agent
    def get(self, *_, **kwargs):
        if "uidb64" not in kwargs or "token" not in kwargs:
            raise ImproperlyConfigured(
                "The URL path must contain 'uidb64' and 'token' parameters."
            )

        user = self.get_user(kwargs["uidb64"])

        if user is not None and user.is_active:
            if GenericToken(request=self.request, purpose=PASS_RESET).check_token(user, kwargs["token"]):

                refresh_token = RefreshToken()
                refresh_token[FOR_USER] = user.id
                refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
                access_token = refresh_token.access_token

                response = HttpResponseRedirect(
                    self.form_url if self.form_url else reverse_lazy('default_password_reset')
                )
                # The form this redirects to has to send a CSRF token back with the new
                # password, so the cookie holding it goes out together with the capability.
                ensure_csrf_cookie(self.request)
                response.set_cookie(
                    key=PASS_RESET_COOKIE,
                    value=str(access_token),
                    httponly=getattr(settings, 'PASSWORD_RESET_COOKIE_HTTP_ONLY', True),
                    secure=getattr(settings, 'PASSWORD_RESET_COOKIE_SECURE', not settings.DEBUG),
                    samesite=getattr(settings, 'PASSWORD_RESET_COOKIE_SAME_SITE', 'Lax'),
                    max_age=getattr(settings, 'PASSWORD_RESET_COOKIE_MAX_AGE', 3600)
                )

                token_serializer = GenericTokenModelSerializer(data={
                    'token': access_token['jti'],
                    'user': user.id,
                    'purpose': PASS_RESET_ACCESS
                })
                token_serializer.is_valid(raise_exception=True)

                with transaction.atomic():
                    # Requesting a second reset must not leave the capability handed out
                    # by an earlier link usable: only the latest one stays alive.
                    GenericTokenModel.objects.filter(user=user, purpose=PASS_RESET_ACCESS).delete()
                    token_serializer.save()

                return response
        return render(self.request, 'password/reset.html', {
            'validlink': False,
            'form': None
        })

    @staticmethod
    def get_user(uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model()._default_manager.get(pk=uid)
        except (
            TypeError,
            ValueError,
            OverflowError,
            get_user_model().DoesNotExist,
            ValidationError,
        ):
            user = None
        return user


@reset_password_schema
class ResetPasswordView(CapabilityCookieViewMixin, ExtraThrottlesMixin, GenericAPIView):
    """
    Calls Django Auth SetPasswordForm save method.

    Accepts the following POST parameters: new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = SetPasswordSerializer
    permission_classes = (ResetPasswordPermission,)
    extra_throttle_classes = (UserRateThrottle,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(ResetPasswordView, self).dispatch(*args, **kwargs)

    def post(self, request):
        # Claim the capability atomically: two requests arriving at once with the same
        # cookie must not both get to set a password.
        if not GenericTokenModel.consume(request.auth['jti'], PASS_RESET_ACCESS):
            raise InvalidToken()

        # Load the user in the request, rejecting an account that has been deleted or
        # deactivated since the capability was issued.
        request.user = load_capability_user(self.request.user.id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Revoke every session, every capability still outstanding and every address
        # change in flight: this is the moment the account changes hands.
        revoke_on_credential_change(self.request.user.id)

        refresh_token = RefreshToken.for_user(request.user)
        return build_token_response(
            refresh_token,
            extra_data={"detail": _("Password reset.")}
        )


@set_password_schema
class SetPasswordView(CapabilityCookieViewMixin, ExtraThrottlesMixin, GenericAPIView):
    """
    Set password for admin-managed registration.
    Accepts: new_password1, new_password2
    Returns: tokens and success message.
    """
    serializer_class = SetPasswordSerializer
    permission_classes = (SetPasswordPermission,)
    extra_throttle_classes = (UserRateThrottle,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        if not invitations_enabled():
            return HttpResponseNotFound()
        return super(SetPasswordView, self).dispatch(*args, **kwargs)

    def post(self, request):
        # Claim the capability atomically: two requests arriving at once with the same
        # cookie must not both get to set a password.
        if not GenericTokenModel.consume(request.auth['jti'], PASS_SET_ACCESS):
            raise InvalidToken()

        # Load the user in the request, rejecting an account that has been deleted or
        # deactivated since the capability was issued.
        request.user = load_capability_user(self.request.user.id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Revoke every session, every capability still outstanding -- the e-mail
        # confirmation token that led here included -- and every address change in
        # flight: this is the moment the account changes hands.
        revoke_on_credential_change(self.request.user.id)

        # The confirmation token is what makes the invitation link re-clickable, so it
        # goes even when the installation opted out of revoking sessions. Both purposes:
        # an invitation carries its own, and the confirmation of an address added later
        # is the one an account that already has a password re-clicks.
        GenericTokenModel.objects.filter(
            user=request.user, purpose__in=(INVITATION, EMAIL_CONFIRMATION)
        ).delete()

        # If MFA TOTP is REQUIRED, return setup challenge instead of tokens
        if get_mfa_totp_mode() == MFA_TOTP_REQUIRED:
            setup_challenge_id = create_setup_challenge(request.user.id)

            return Response(
                {
                    "mfa_setup_required": True,
                    "setup_challenge_id": setup_challenge_id,
                    "detail": _("Password set. Please configure MFA to complete registration."),
                },
                status=status.HTTP_200_OK,
            )

        refresh_token = RefreshToken.for_user(request.user)
        return build_token_response(
            refresh_token,
            extra_data={"detail": _("Password set.")}
        )
