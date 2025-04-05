from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle

from jwt_allauth.app_settings import LoginSerializer
from jwt_allauth.utils import get_user_agent, sensitive_post_parameters_m


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

        return Response(
            {
                "access": serializer.validated_data['access'],
                "refresh": serializer.validated_data['refresh'],
            }, status=status.HTTP_200_OK
        )
