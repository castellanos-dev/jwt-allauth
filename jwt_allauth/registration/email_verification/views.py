from datetime import timedelta

from allauth.account import app_settings as allauth_app_settings
from allauth.account.views import ConfirmEmailView
from allauth.account.models import EmailAddress
from django.conf import settings
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken

from jwt_allauth.constants import (
    EMAIL_VERIFIED_REDIRECT,
    PASSWORD_SET_REDIRECT,
    FOR_USER,
    ONE_TIME_PERMISSION,
    PASS_SET_ACCESS,
    REFRESH_TOKEN_COOKIE,
    SET_PASSWORD_COOKIE,
    EMAIL_CONFIRMATION,
    EMAIL_VERIFICATION_FAILED_TEMPLATE,
)
from jwt_allauth.registration.email_verification.serializers import VerifyEmailSerializer
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.tokens.serializers import GenericTokenModelSerializer
from jwt_allauth.utils import (
    _get_cookie_max_age,
    _get_cookie_secure,
    get_template_path,
    get_user_agent,
    hash_token,
)


class VerifyEmailView(APIView, ConfirmEmailView):
    permission_classes = (AllowAny,)
    allowed_methods = ('GET',)
    # URL where the frontend password-set flow is implemented (admin-managed registration)
    # By default, point to the built-in HTML UI provided by this library.
    form_url = getattr(settings, PASSWORD_SET_REDIRECT, '/registration/set-password/default/')

    @staticmethod
    def get_serializer(*args, **kwargs):
        return VerifyEmailSerializer(*args, **kwargs)

    def _verification_failed(self, request):
        return render(
            request,
            get_template_path(EMAIL_VERIFICATION_FAILED_TEMPLATE, 'registration/verification_failed.html'),
            status=400
        )

    @staticmethod
    def _start_session(response, request, user):
        """
        Hand the browser that followed the link a session, as a refresh token cookie.

        Registration cannot deliver that session itself: while address conflicts are
        hidden it issues no token at all, and even when it does, the token belongs to
        whichever client filled in the form, which is often not the one the link is
        opened on. Here the account has just proven control over the mailbox, which is
        the same standing the password reset link is already given.

        Off unless ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION`` is enabled: it turns
        the confirmation link into a credential, so whoever the mail reaches -- a
        forwarded copy, a shared inbox -- lands on the account logged in rather than
        only confirming the address.

        Args:
            response (HttpResponse): Redirect the cookie is attached to.
            request (HttpRequest): Request being served.
            user (AbstractBaseUser): Owner of the address that was just confirmed.
        """
        if not getattr(settings, 'JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION', False):
            return
        if not getattr(settings, 'JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE', True):
            # Installations that carry refresh tokens in the response body have no
            # body to carry it in here, and the URL is not an option: it would end up
            # in the browser history and in every log along the way.
            return

        refresh_token = RefreshToken.for_user(user, request, enabled=True)
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE,
            value=str(refresh_token),
            httponly=getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_HTTP_ONLY", True),
            secure=_get_cookie_secure(),
            samesite=getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SAME_SITE", "Lax"),
            max_age=_get_cookie_max_age(),
            path=getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_PATH", "/"),
        )

    @get_user_agent
    def get(self, request, *args, **kwargs):
        # If admin-managed registration is enabled, validate the confirmation key and
        # issue a one-time token to allow the user to set their password.
        if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
            # Ensure PASSWORD_SET_REDIRECT has been configured
            if self.form_url is None:
                raise NotImplementedError('`PASSWORD_SET_REDIRECT` must be configured in settings.py')

            # Check that the email confirmation token exists and is still within allauth's
            # confirmation window. Note: For admin-managed registration, we allow multi-use
            # until password is set, but never beyond the expiration of the confirmation
            # itself: allauth's own expiry check is bypassed by the `except` clause below,
            # so the age of the key has to be enforced here as well.
            cutoff = timezone.now() - timedelta(
                days=allauth_app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS
            )
            # Keys are stored as digests. In-flight confirmations issued by a previous
            # version are still stored in plain text, so they are accepted as well until
            # they expire.
            token_entry = GenericTokenModel.objects.filter(
                token__in=(hash_token(kwargs['key']), kwargs['key']),
                purpose=EMAIL_CONFIRMATION,
                created__gte=cutoff,
            ).first()
            if token_entry is None:
                return self._verification_failed(request)

            user = token_entry.user

            # The password-set capability only makes sense for an invited account that has
            # not chosen a password yet. Issuing it for an account that already has one
            # would turn any confirmation link into a password reset link, bypassing the
            # reset flow and its throttling.
            if user.has_usable_password():
                return self._verification_failed(request)

            try:
                confirmation = self.get_object()
                confirmation.confirm(self.request)
            except (Http404, InvalidToken):
                # allauth rejects the key once the address has been confirmed, so a second
                # click on the same link lands here (multi-use). Expiration is already
                # covered by `cutoff` above; anything else is a genuine error.
                # Note: We use the user from our GenericTokenModel which we know is valid.
                if not EmailAddress.objects.filter(user=user, verified=True).exists():
                    return self._verification_failed(request)

            # Create one-time access token to allow setting the password
            refresh_token = RefreshToken()
            refresh_token[FOR_USER] = user.id
            refresh_token[ONE_TIME_PERMISSION] = PASS_SET_ACCESS
            access_token = refresh_token.access_token

            response = HttpResponseRedirect(self.form_url)
            response.set_cookie(
                key=SET_PASSWORD_COOKIE,
                value=str(access_token),
                httponly=getattr(settings, 'PASSWORD_SET_COOKIE_HTTP_ONLY', True),
                secure=getattr(settings, 'PASSWORD_SET_COOKIE_SECURE', not settings.DEBUG),
                samesite=getattr(settings, 'PASSWORD_SET_COOKIE_SAME_SITE', 'Lax'),
                max_age=getattr(settings, 'PASSWORD_SET_COOKIE_MAX_AGE', 3600 * 24),
            )

            # Re-clicking the verification link is allowed until the password is set, but
            # only the capability handed out by the latest click stays valid.
            GenericTokenModel.objects.filter(user=user, purpose=PASS_SET_ACCESS).delete()

            token_serializer = GenericTokenModelSerializer(
                data={
                    'token': access_token['jti'],
                    'user': user.id,
                    'purpose': PASS_SET_ACCESS,
                }
            )
            token_serializer.is_valid(raise_exception=True)
            token_serializer.save()

            return response

        # Default flow: just confirm the email and enable refresh tokens
        confirmation = self.get_object()
        user = confirmation.email_address.user

        # Enable refresh token
        refresh = RefreshTokenWhitelistModel.objects.filter(user=user).first()
        if refresh:
            refresh.enabled = True
            refresh.save()

        # Only the sign-up confirmation completes a registration. Confirming a
        # secondary address added later to an account that is already usable is not an
        # invitation to open a session on the browser that happened to receive it.
        completes_signup = not EmailAddress.objects.filter(user=user, verified=True).exists()

        confirmation.confirm(self.request)

        response = HttpResponseRedirect(
            getattr(settings, EMAIL_VERIFIED_REDIRECT, reverse('jwt_allauth_email_verified'))
        )
        if completes_signup:
            self._start_session(response, request, user)
        return response

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])
