from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from jwt_allauth.app_settings import PasswordChangeSerializer
from jwt_allauth.schema import password_change_schema
from jwt_allauth.throttling import ExtraThrottlesMixin
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.utils import (
    build_token_response,
    get_user_agent,
    load_capability_user,
    sensitive_post_parameters_m,
)


@password_change_schema
class PasswordChangeView(ExtraThrottlesMixin, GenericAPIView):
    """
    Change the password of the authenticated account.

    Accepts the following POST parameters: new_password1, new_password2, and
    old_password while ``OLD_PASSWORD_FIELD_ENABLED`` is on. Unless
    ``LOGOUT_ON_PASSWORD_CHANGE = False``, every session is revoked -- the caller's
    included -- and the response carries a replacement session minted after the change.
    """
    serializer_class = PasswordChangeSerializer
    permission_classes = (IsAuthenticated,)
    extra_throttle_classes = (UserRateThrottle,)

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(PasswordChangeView, self).dispatch(*args, **kwargs)

    @get_user_agent
    def post(self, request):
        # Load the user in the request, rejecting an account that has been deleted or
        # deactivated since the access token was issued: this flow ends by opening a
        # session, and a deactivated account has none -- login and refresh both refuse
        # it. Without the check it was the last way back into a disabled account.
        request.user = load_capability_user(self.request.user.id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        detail = {"detail": _("New password has been saved.")}

        if not getattr(settings, 'LOGOUT_ON_PASSWORD_CHANGE', True):
            # Nothing was revoked, so the caller keeps the session it came in with.
            return Response(detail)

        # Every session was revoked, the caller's included. It gets a new one, minted
        # after the change, rather than an exemption from the revocation.
        return build_token_response(
            RefreshToken.for_user(request.user, request),
            extra_data=detail,
        )
