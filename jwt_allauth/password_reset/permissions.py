from rest_framework.permissions import BasePermission as DefaultBasePermission
from rest_framework_simplejwt.exceptions import TokenError

from jwt_allauth.constants import PASS_RESET_ACCESS, PASS_RESET_COOKIE, FOR_USER, ONE_TIME_PERMISSION, \
    PASS_SET_ACCESS, SET_PASSWORD_COOKIE
from jwt_allauth.password_reset.models import SetPasswordTokenUser
from jwt_allauth.tokens.app_settings import RefreshToken


class _BaseOneTimeCookiePermission(DefaultBasePermission):
    """
    Base permission that validates a one-time access token from a specific cookie
    and injects a SetPasswordTokenUser into the request.
    Subclasses must define COOKIE_NAME and REQUIRED_PERMISSION.
    """
    COOKIE_NAME = None
    REQUIRED_PERMISSION = None

    def has_permission(self, request, view):
        if bool(request.user and request.user.is_authenticated):
            return False
        if not self.COOKIE_NAME or not self.REQUIRED_PERMISSION:
            return False
        if hasattr(request, 'COOKIES') and self.COOKIE_NAME in request.COOKIES:
            access_token = request.COOKIES.get(self.COOKIE_NAME)
            try:
                access_token = RefreshToken.access_token_class(access_token)
            except TokenError:
                return False
            if access_token and ONE_TIME_PERMISSION in access_token and FOR_USER in access_token:
                if access_token[ONE_TIME_PERMISSION] == self.REQUIRED_PERMISSION:
                    request.user = SetPasswordTokenUser(access_token)
                    request.auth = access_token
                    return True
        return False


class ResetPasswordPermission(_BaseOneTimeCookiePermission):
    COOKIE_NAME = PASS_RESET_COOKIE
    REQUIRED_PERMISSION = PASS_RESET_ACCESS


class SetPasswordPermission(_BaseOneTimeCookiePermission):
    COOKIE_NAME = SET_PASSWORD_COOKIE
    REQUIRED_PERMISSION = PASS_SET_ACCESS
