from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenRefreshView as DefaultTokenRefreshView
from rest_framework.throttling import UserRateThrottle

from jwt_allauth.token_refresh.serializers import TokenRefreshSerializer
from jwt_allauth.utils import get_user_agent, user_agent_dict


class TokenRefreshView(DefaultTokenRefreshView):
    serializer_class = TokenRefreshSerializer
    throttle_classes = [UserRateThrottle]

    @get_user_agent
    def post(self, request: Request, *args, **kwargs) -> Response:
        input_data = {}
        if 'refresh' in request.data:
            input_data['refresh'] = request.data['refresh']
        context = user_agent_dict(self.request)
        serializer = self.get_serializer(data=input_data, context=context)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
