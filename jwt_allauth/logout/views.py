from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from jwt_allauth.logout.serializers import RemoveRefreshTokenSerializer
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.constants import REFRESH_TOKEN_COOKIE
from jwt_allauth.utils import refresh_token_as_cookie, user_sessions_lock


class LogoutView(APIView):
    """
    Calls Django logout method and delete the Token object
    assigned to the current User object.

    Accepts/Returns nothing.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def post(self, request):
        return self.logout(request)

    @staticmethod
    def logout(request):
        data = request.data.copy()

        # Through the helper, never by re-reading the setting here. This endpoint is the
        # only one that *consumes* the refresh token; every endpoint that issues one goes
        # through `refresh_token_as_cookie()`, which defaults to True. Reading the setting
        # again with a default of its own made the two disagree wherever the project had
        # not declared it -- the default case: the token went out as an HttpOnly cookie
        # and this view looked for it in a body the frontend had no way to fill, so
        # `refresh` came back "required" and logout closed nothing at all. One reader
        # cannot drift from itself.
        if refresh_token_as_cookie():
            refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE)
            if refresh_token:
                data['refresh'] = refresh_token
            else:
                return Response(
                    {"detail": _("Refresh token cookie not found.")},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            RemoveRefreshTokenSerializer(
                data=data,
                context={'user': request.user.id}
            ).is_valid(raise_exception=True)
            return Response(
                {"detail": _("Successfully logged out.")},
                status=status.HTTP_200_OK
            )
        except (TokenError, InvalidToken):
            return Response(
                {"detail": _("Invalid token.")},
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutAllView(APIView):
    """
    Logout from all devices.

    Accepts/Returns nothing.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return self.http_method_not_allowed(request, *args, **kwargs)

    def post(self, request):
        return self.logout(request)

    @staticmethod
    def logout(request):
        # Under the lock: a refresh rotating one of these sessions concurrently would
        # otherwise insert its successor where this deletion cannot see it, and the
        # session would survive the logout.
        with user_sessions_lock(request.user.id):
            RefreshTokenWhitelistModel.objects.filter(user=request.user.id).delete()
        return Response(
            {"detail": _("Successfully logged out from all devices.")},
            status=status.HTTP_200_OK
        )
