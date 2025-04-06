from allauth.account.views import ConfirmEmailView
from django.http import HttpResponseRedirect, HttpResponseNotAllowed
from django.urls import reverse
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from jwt_allauth.constants import EMAIL_VERIFIED_REDIRECT
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.registration.email_verification.serializers import VerifyEmailSerializer


class VerifyEmailView(APIView, ConfirmEmailView):
    permission_classes = (AllowAny,)
    allowed_methods = ('GET',)

    @staticmethod
    def get_serializer(*args, **kwargs):
        return VerifyEmailSerializer(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        confirmation = self.get_object()

        # Enable refresh token
        refresh = RefreshTokenWhitelistModel.objects.filter(user=confirmation.email_address.user).first()
        if refresh:
            refresh.enabled = True
            refresh.save()

        confirmation.confirm(self.request)
        return HttpResponseRedirect(getattr(settings, EMAIL_VERIFIED_REDIRECT, reverse('jwt_allauth_email_verified')))

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])
