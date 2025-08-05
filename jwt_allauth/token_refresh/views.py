from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenRefreshView as DefaultTokenRefreshView
from rest_framework.throttling import UserRateThrottle
from jwt_allauth.token_refresh.serializers import TokenRefreshSerializer
from jwt_allauth.utils import get_user_agent, user_agent_dict
from jwt_allauth.constants import REFRESH_TOKEN_COOKIE


class TokenRefreshView(DefaultTokenRefreshView):
    serializer_class = TokenRefreshSerializer
    throttle_classes = [UserRateThrottle]

    @get_user_agent
    def post(self, request: Request, *args, **kwargs) -> Response:
        input_data = {}

        # Get refresh token from cookie or request data based on configuration
        if getattr(settings, 'JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE', True):
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                input_data['refresh'] = refresh_token
        else:
            if 'refresh' in request.data:
                input_data['refresh'] = request.data['refresh']

        context = user_agent_dict(self.request)
        serializer = self.get_serializer(data=input_data, context=context)

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
