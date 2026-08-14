from rest_framework_simplejwt.exceptions import AuthenticationFailed, DetailDictMixin

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


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


# Social authentication.
#
# An unverified account and an inactive one are deliberately absent: those answers must
# be indistinguishable from the ones the password login gives, so the social flow raises
# `NotVerifiedEmail` and simplejwt's `no_active_account` rather than reasons of its own.

class SocialAPIException(DetailDictMixin, APIException):
    """
    Base of the social errors, answering with a ``code`` beside the ``detail``.

    The errors this library already raised carry one, because they inherit simplejwt's
    exceptions, and clients switch on it -- a localized ``detail`` is for a person to
    read, not for a frontend to branch on. The same mixin is used here so that the
    social endpoints do not answer in a shape of their own.
    """


class SocialProviderNotConfigured(SocialAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("This provider is not configured.")
    default_code = "provider_not_configured"


class SocialFlowNotSupported(SocialAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This provider does not support this authentication flow.")
    default_code = "flow_not_supported"


class SocialTokenInvalid(SocialAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("The provider rejected the credential.")
    default_code = "invalid_social_token"


class SocialEmailUnverified(SocialAPIException):
    """
    The provider did not vouch for an address.

    An account here is email-only, and an address nobody has vouched for cannot be
    confirmed later either: there is no password to reset and no link worth sending.
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The provider did not supply a verified e-mail address.")
    default_code = "provider_email_unverified"


class SocialAccountAlreadyConnected(SocialAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This provider account is already connected to another user.")
    default_code = "social_account_in_use"


class SocialEmailConflict(SocialAPIException):
    """
    The address belongs to somebody else's account and linking is switched off.

    Raised only when ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING`` excludes the provider; with
    linking on -- the default -- a provider-verified address links instead.
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("A user is already registered with this e-mail address.")
    default_code = "email_already_registered"


class SocialSignupClosed(SocialAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("Registration is closed.")
    default_code = "signup_closed"


class SocialSignupNotAllowed(SocialAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Signing up through a provider is not allowed.")
    default_code = "signup_not_allowed"


class SocialLoginRejected(SocialAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("This social login was rejected.")
    default_code = "social_login_rejected"


class SocialDisconnectNotAllowed(SocialAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This provider cannot be disconnected.")
    default_code = "disconnect_not_allowed"
