from allauth.account.views import ConfirmEmailView
from allauth.account.models import EmailAddress
from django.conf import settings
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.constants import (
    EMAIL_VERIFIED_REDIRECT,
    PASSWORD_SET_REDIRECT,
    FOR_USER,
    ONE_TIME_PERMISSION,
    PASS_SET_ACCESS,
    SET_PASSWORD_COOKIE,
    EMAIL_CONFIRMATION,
    EMAIL_VERIFICATION_FAILED_TEMPLATE,
)
from jwt_allauth.registration.email_verification.serializers import VerifyEmailSerializer
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.tokens.serializers import GenericTokenModelSerializer
from jwt_allauth.utils import get_template_path


class VerifyEmailView(APIView, ConfirmEmailView):
    permission_classes = (AllowAny,)
    allowed_methods = ('GET',)
    # URL where the frontend password-set flow is implemented (admin-managed registration)
    # By default, point to the built-in HTML UI provided by this library.
    form_url = getattr(settings, PASSWORD_SET_REDIRECT, '/registration/set-password/default/')

    @staticmethod
    def get_serializer(*args, **kwargs):
        return VerifyEmailSerializer(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        # If admin-managed registration is enabled, validate the confirmation key and
        # issue a one-time token to allow the user to set their password.
        if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
            # Ensure PASSWORD_SET_REDIRECT has been configured
            if self.form_url is None:
                raise NotImplementedError('`PASSWORD_SET_REDIRECT` must be configured in settings.py')

            # Check that the email confirmation token has not been used already
            # Note: For admin-managed registration, we allow multi-use until password is set.
            try:
                token_entry = GenericTokenModel.objects.get(
                    token=kwargs['key'],
                    purpose=EMAIL_CONFIRMATION,
                )
            except GenericTokenModel.DoesNotExist:
                return render(
                    request,
                    get_template_path(EMAIL_VERIFICATION_FAILED_TEMPLATE, 'registration/verification_failed.html'),
                    status=400
                )

            user = token_entry.user

            try:
                confirmation = self.get_object()
                confirmation.confirm(self.request)
            except (Http404, InvalidToken):
                # If allauth fails to verify (e.g. expired or already verified state issues),
                # check if the user is already verified. If so, allow proceeding (multi-use).
                # If not verified, then it's a genuine error/expiration.
                # Note: We use the user from our GenericTokenModel which we know is valid.
                if not EmailAddress.objects.filter(user=user, verified=True).exists():
                    return render(
                        request,
                        get_template_path(EMAIL_VERIFICATION_FAILED_TEMPLATE, 'registration/verification_failed.html'),
                        status=400
                    )

            # Create one-time access token to allow setting the password
            refresh_token = RefreshToken()
            refresh_token[FOR_USER] = user.id
            refresh_token[ONE_TIME_PERMISSION] = PASS_SET_ACCESS
            access_token = refresh_token.access_token

            response = HttpResponseRedirect(self.form_url)
            response.set_cookie(
                key=SET_PASSWORD_COOKIE,
                value=str(access_token),
                httponly=getattr(settings, 'PASSWORD_SET_COOKIE_HTTP_ONLY', True),
                secure=getattr(settings, 'PASSWORD_SET_COOKIE_SECURE', not settings.DEBUG),
                samesite=getattr(settings, 'PASSWORD_SET_COOKIE_SAME_SITE', 'Lax'),
                max_age=getattr(settings, 'PASSWORD_SET_COOKIE_MAX_AGE', 3600 * 24),
            )

            token_serializer = GenericTokenModelSerializer(
                data={
                    'token': access_token['jti'],
                    'user': user.id,
                    'purpose': PASS_SET_ACCESS,
                }
            )
            token_serializer.is_valid(raise_exception=True)
            token_serializer.save()

            return response

        # Default flow: just confirm the email and enable refresh tokens
        confirmation = self.get_object()

        # Enable refresh token
        refresh = RefreshTokenWhitelistModel.objects.filter(user=confirmation.email_address.user).first()
        if refresh:
            refresh.enabled = True
            refresh.save()

        confirmation.confirm(self.request)
        return HttpResponseRedirect(
            getattr(settings, EMAIL_VERIFIED_REDIRECT, reverse('jwt_allauth_email_verified'))
        )

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])
