from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenRefreshView as DefaultTokenRefreshView
from rest_framework.throttling import UserRateThrottle
from jwt_allauth.constants import REFRESH_TOKEN_COOKIE
from jwt_allauth.token_refresh.serializers import TokenRefreshSerializer
from jwt_allauth.utils import (
    get_user_agent,
    refresh_token_as_cookie,
    set_refresh_token_cookie,
    user_agent_dict,
)
from jwt_allauth.schema import token_refresh_schema
from jwt_allauth.throttling import ExtraThrottlesMixin


@token_refresh_schema
class TokenRefreshView(ExtraThrottlesMixin, DefaultTokenRefreshView):
    """
    Rotate a refresh token: returns a new access token and a new refresh token.

    The refresh token is read from the ``refresh_token`` cookie, or from the ``refresh``
    field of the body when ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``, and is
    delivered back the same way. The token presented is consumed: presenting it twice
    is treated as a replay and closes the session.
    """
    serializer_class = TokenRefreshSerializer
    extra_throttle_classes = (UserRateThrottle,)

    @get_user_agent
    def post(self, request: Request, *args, **kwargs) -> Response:
        input_data = {}

        # Get refresh token from cookie or request data based on configuration
        if refresh_token_as_cookie():
            refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE)
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
        if not refresh_token_as_cookie():
            response_data["refresh"] = serializer.validated_data['refresh']

        response = Response(response_data, status=status.HTTP_200_OK)

        if refresh_token_as_cookie():
            set_refresh_token_cookie(response, serializer.validated_data['refresh'])

        return response
