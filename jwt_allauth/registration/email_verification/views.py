from datetime import timedelta

from allauth.account import app_settings as allauth_app_settings
from allauth.account.views import ConfirmEmailView
from allauth.account.models import EmailAddress
from django.conf import settings
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
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
from jwt_allauth.utils import get_template_path, hash_token


class VerifyEmailView(APIView, ConfirmEmailView):
    permission_classes = (AllowAny,)
    allowed_methods = ('GET',)
    # URL where the frontend password-set flow is implemented (admin-managed registration)
    # By default, point to the built-in HTML UI provided by this library.
    form_url = getattr(settings, PASSWORD_SET_REDIRECT, '/registration/set-password/default/')

    @staticmethod
    def get_serializer(*args, **kwargs):
        return VerifyEmailSerializer(*args, **kwargs)

    def _verification_failed(self, request):
        return render(
            request,
            get_template_path(EMAIL_VERIFICATION_FAILED_TEMPLATE, 'registration/verification_failed.html'),
            status=400
        )

    def get(self, request, *args, **kwargs):
        # If admin-managed registration is enabled, validate the confirmation key and
        # issue a one-time token to allow the user to set their password.
        if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
            # Ensure PASSWORD_SET_REDIRECT has been configured
            if self.form_url is None:
                raise NotImplementedError('`PASSWORD_SET_REDIRECT` must be configured in settings.py')

            # Check that the email confirmation token exists and is still within allauth's
            # confirmation window. Note: For admin-managed registration, we allow multi-use
            # until password is set, but never beyond the expiration of the confirmation
            # itself: allauth's own expiry check is bypassed by the `except` clause below,
            # so the age of the key has to be enforced here as well.
            cutoff = timezone.now() - timedelta(
                days=allauth_app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS
            )
            # Keys are stored as digests. In-flight confirmations issued by a previous
            # version are still stored in plain text, so they are accepted as well until
            # they expire.
            token_entry = GenericTokenModel.objects.filter(
                token__in=(hash_token(kwargs['key']), kwargs['key']),
                purpose=EMAIL_CONFIRMATION,
                created__gte=cutoff,
            ).first()
            if token_entry is None:
                return self._verification_failed(request)

            user = token_entry.user

            # The password-set capability only makes sense for an invited account that has
            # not chosen a password yet. Issuing it for an account that already has one
            # would turn any confirmation link into a password reset link, bypassing the
            # reset flow and its throttling.
            if user.has_usable_password():
                return self._verification_failed(request)

            try:
                confirmation = self.get_object()
                confirmation.confirm(self.request)
            except (Http404, InvalidToken):
                # allauth rejects the key once the address has been confirmed, so a second
                # click on the same link lands here (multi-use). Expiration is already
                # covered by `cutoff` above; anything else is a genuine error.
                # Note: We use the user from our GenericTokenModel which we know is valid.
                if not EmailAddress.objects.filter(user=user, verified=True).exists():
                    return self._verification_failed(request)

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

            # Re-clicking the verification link is allowed until the password is set, but
            # only the capability handed out by the latest click stays valid.
            GenericTokenModel.objects.filter(user=user, purpose=PASS_SET_ACCESS).delete()

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
