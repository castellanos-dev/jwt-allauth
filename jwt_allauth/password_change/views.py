from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from jwt_allauth.app_settings import PasswordChangeSerializer
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.utils import build_token_response, get_user_agent, sensitive_post_parameters_m


class PasswordChangeView(GenericAPIView):
    """
    Calls Django Auth SetPasswordForm save method.

    Accepts the following POST parameters: new_password1, new_password2
    Returns the success/fail message.
    """
    serializer_class = PasswordChangeSerializer
    permission_classes = (IsAuthenticated,)
    throttle_classes = [UserRateThrottle]

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super(PasswordChangeView, self).dispatch(*args, **kwargs)

    @get_user_agent
    def post(self, request):
        # Load the user in the request
        request.user = get_user_model().objects.get(id=self.request.user.id)
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
