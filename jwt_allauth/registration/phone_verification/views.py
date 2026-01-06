from django.utils.translation import gettext_lazy as _
from rest_framework import status, views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from jwt_allauth.registration.phone_verification.serializers import VerifyPhoneSerializer, ResendPhoneSerializer
from jwt_allauth.tokens.app_settings import RefreshToken


class VerifyPhoneView(views.APIView):
    permission_classes = (AllowAny,)
    serializer_class = VerifyPhoneSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirmation = serializer.validated_data['confirmation']
        phone_address = confirmation.confirm(request)
        user = phone_address.user

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'detail': _('Phone number verified.'),
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )


class ResendPhoneView(views.APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResendPhoneSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_address = serializer.validated_data['phone_address']
        phone_address.send_confirmation(request)

        return Response(
            {
                'detail': _('Verification SMS sent.'),
            },
            status=status.HTTP_200_OK,
        )
