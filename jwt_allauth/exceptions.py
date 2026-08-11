from rest_framework_simplejwt.exceptions import AuthenticationFailed

from django.utils.translation import gettext_lazy as _
from rest_framework import status


class NotVerifiedEmail(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("User email is not verified")
    default_code = "email_not_verified"


class SessionExpired(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Session reached its maximum lifetime. Please log in again")
    default_code = "session_expired"


class IncorrectCredentials(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Incorrect credentials")
    default_code = "incorrect_credentials"
