from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle

from jwt_allauth.app_settings import LoginSerializer
from jwt_allauth.utils import get_user_agent, sensitive_post_parameters_m
from jwt_allauth.constants import REFRESH_TOKEN_COOKIE


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [AnonRateThrottle]

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    @get_user_agent
    def post(self, request: Request, *args, **kwargs) -> Response:
        # Authenticate and generate the tokens
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        response_data = {"access": serializer.validated_data['access']}

        # Handle refresh token based on configuration
        if not getattr(settings, 'JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE', True):
            response_data["refresh"] = serializer.validated_data['refresh']

        response = Response(response_data, status=status.HTTP_200_OK)

        if getattr(settings, 'JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE', True):
            response.set_cookie(
                key=REFRESH_TOKEN_COOKIE,
                value=str(serializer.validated_data['refresh']),
                httponly=True,
                secure=not settings.DEBUG if hasattr(settings, 'DEBUG') else True,
                samesite='Lax'
            )

        return response
