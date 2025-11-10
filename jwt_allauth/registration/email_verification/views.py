from allauth.account.views import ConfirmEmailView
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.urls import reverse
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from jwt_allauth.constants import EMAIL_VERIFIED_REDIRECT, PASSWORD_SET_REDIRECT, \
    FOR_USER, ONE_TIME_PERMISSION, PASS_SET_ACCESS, SET_PASSWORD_COOKIE
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.registration.email_verification.serializers import VerifyEmailSerializer
from jwt_allauth.tokens.serializers import GenericTokenModelSerializer
from jwt_allauth.tokens.app_settings import RefreshToken


class VerifyEmailView(APIView, ConfirmEmailView):
    permission_classes = (AllowAny,)
    allowed_methods = ('GET',)

    @staticmethod
    def get_serializer(*args, **kwargs):
        return VerifyEmailSerializer(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        confirmation = self.get_object()

        # If admin-managed registration is enabled, issue a one-time access token to set password
        if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
            user = confirmation.email_address.user
            # In admin-managed mode, confirm email now
            confirmation.confirm(self.request)

            refresh_token = RefreshToken()
            refresh_token[FOR_USER] = user.id
            refresh_token[ONE_TIME_PERMISSION] = PASS_SET_ACCESS
            access_token = refresh_token.access_token

            # In admin-managed mode, PASSWORD_SET_REDIRECT should be configured
            # to point to the frontend page where users set their password
            redirect_url = getattr(settings, PASSWORD_SET_REDIRECT, '/set-password/')
            response = HttpResponseRedirect(redirect_url)
            response.set_cookie(
                key=SET_PASSWORD_COOKIE,
                value=str(access_token),
                httponly=getattr(settings, 'PASSWORD_SET_COOKIE_HTTP_ONLY', True),
                secure=getattr(settings, 'PASSWORD_SET_COOKIE_SECURE', not settings.DEBUG),
                samesite=getattr(settings, 'PASSWORD_SET_COOKIE_SAME_SITE', 'Lax'),
                max_age=getattr(settings, 'PASSWORD_SET_COOKIE_MAX_AGE', 3600 * 24)
            )

            token_serializer = GenericTokenModelSerializer(data={
                'token': access_token['jti'],
                'user': user.id,
                'purpose': PASS_SET_ACCESS
            })
            token_serializer.is_valid(raise_exception=True)
            token_serializer.save()

            return response
        else:
            # Enable refresh token
            refresh = RefreshTokenWhitelistModel.objects.filter(user=confirmation.email_address.user).first()
            if refresh:
                refresh.enabled = True
                refresh.save()

            confirmation.confirm(self.request)
            return HttpResponseRedirect(
                getattr(settings, EMAIL_VERIFIED_REDIRECT, reverse('jwt_allauth_email_verified')))

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])
