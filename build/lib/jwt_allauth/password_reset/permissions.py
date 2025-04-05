from rest_framework.permissions import BasePermission as DefaultBasePermission
from rest_framework_simplejwt.exceptions import TokenError

from jwt_allauth.constants import PASS_RESET_ACCESS, PASS_RESET_COOKIE, FOR_USER, ONE_TIME_PERMISSION
from jwt_allauth.password_reset.models import SetPasswordTokenUser
from jwt_allauth.token.app_settings import RefreshToken


class ResetPasswordPermission(DefaultBasePermission):

    def has_permission(self, request, view):
        if bool(request.user and request.user.is_authenticated):
            # the user is authenticated: unexpected behaviour
            return False
        if hasattr(request, 'COOKIES') and PASS_RESET_COOKIE in request.COOKIES:
            access_token = request.COOKIES.get(PASS_RESET_COOKIE)
            try:
                access_token = RefreshToken.access_token_class(access_token)
            except TokenError:
                return False
            if access_token and ONE_TIME_PERMISSION in access_token and FOR_USER in access_token:
                if access_token[ONE_TIME_PERMISSION] == PASS_RESET_ACCESS:
                    request.user = SetPasswordTokenUser(access_token)
                    request.auth = access_token
                    return True
        return False
