from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.app_settings import PasswordResetSerializer
from jwt_allauth.constants import PASS_RESET, PASSWORD_RESET_REDIRECT, FOR_USER, \
    ONE_TIME_PERMISSION, PASS_SET_ACCESS, PASS_RESET_ACCESS, PASS_RESET_COOKIE
from jwt_allauth.password_reset.permissions import ResetPasswordPermission, SetPasswordPermission
from jwt_allauth.password_reset.serializers import SetPasswordSerializer
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.tokens.serializers import GenericTokenModelSerializer
from jwt_allauth.tokens.tokens import GenericToken
from jwt_allauth.utils import get_user_agent, sensitive_post_parameters_m, build_token_response


class PasswordResetView(GenericAPIView):
    """
    Calls Django Auth PasswordResetForm save method.

    Accepts the following POST parameters: email
    Returns the success/fail message.
    """
    serializer_class = PasswordResetSerializer
    permission_classes = (AllowAny,)
    throttle_classes = [AnonRateThrottle]

    @get_user_agent
    def post(self, request):
        # Create a serializer with request.data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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


class PasswordResetConfirmView(GenericAPIView):
    form_url = getattr(settings, PASSWORD_RESET_REDIRECT, None)

    @get_user_agent
    def get(self, *_, **kwargs):
        if "uidb64" not in kwargs or "token" not in kwargs:
            raise ImproperlyConfigured(
                "The URL path must contain 'uidb64' and 'token' parameters."
            )

        user = self.get_user(kwargs["uidb64"])

        if user is not None:
            if GenericToken(request=self.request, purpose=PASS_RESET).check_token(user, kwargs["token"]):

                refresh_token = RefreshToken()
                refresh_token[FOR_USER] = user.id
                refresh_token[ONE_TIME_PERMISSION] = PASS_RESET_ACCESS
                access_token = refresh_token.access_token

                response = HttpResponseRedirect(
                    self.form_url if self.form_url else reverse_lazy('default_password_reset')
                )
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


class ResetPasswordView(GenericAPIView):
    """
    Calls Django Auth SetPasswordForm save method.

    Accepts the following POST parameters: new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = SetPasswordSerializer
    permission_classes = (ResetPasswordPermission,)
    throttle_classes = [UserRateThrottle]

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(ResetPasswordView, self).dispatch(*args, **kwargs)

    def post(self, request):
        # check the token has not been used
        query_set = GenericTokenModel.objects.filter(token=request.auth['jti'], purpose=PASS_RESET_ACCESS)
        if len(query_set) != 1:
            raise InvalidToken()
        query_set.delete()  # single use

        # Load the user in the request
        request.user = get_user_model().objects.get(id=self.request.user.id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Revoke old sessions
        if getattr(settings, 'LOGOUT_ON_PASSWORD_CHANGE', True):
            RefreshTokenWhitelistModel.objects.filter(user=self.request.user.id).delete()

        refresh_token = RefreshToken.for_user(request.user)
        return build_token_response(
            refresh_token,
            extra_data={"detail": _("Password reset.")}
        )


class SetPasswordView(GenericAPIView):
    """
    Set password for admin-managed registration.
    Accepts: new_password1, new_password2
    Returns: tokens and success message.
    """
    serializer_class = SetPasswordSerializer
    permission_classes = (SetPasswordPermission,)
    throttle_classes = [UserRateThrottle]

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        if not getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
            return HttpResponseNotFound()
        return super(SetPasswordView, self).dispatch(*args, **kwargs)

    def post(self, request):
        # check the token has not been used
        query_set = GenericTokenModel.objects.filter(token=request.auth['jti'], purpose=PASS_SET_ACCESS)
        if len(query_set) != 1:
            raise InvalidToken()
        query_set.delete()  # single use

        # Load the user in the request
        request.user = get_user_model().objects.get(id=self.request.user.id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Revoke old sessions
        if getattr(settings, 'LOGOUT_ON_PASSWORD_CHANGE', True):
            RefreshTokenWhitelistModel.objects.filter(user=self.request.user.id).delete()

        refresh_token = RefreshToken.for_user(request.user)
        return build_token_response(
            refresh_token,
            extra_data={"detail": _("Password set.")}
        )
