from datetime import timedelta

from allauth.account import app_settings as allauth_app_settings
from allauth.account.views import ConfirmEmailView
from allauth.account.models import EmailAddress
from django.conf import settings
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
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
    SET_PASSWORD_COOKIE,
    EMAIL_CONFIRMATION,
    EMAIL_VERIFICATION_FAILED_TEMPLATE,
    INVITATION,
)
from jwt_allauth.csrf import ensure_csrf_cookie
from jwt_allauth.registration.email_verification.serializers import VerifyEmailSerializer
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.tokens.serializers import GenericTokenModelSerializer
from jwt_allauth.utils import (
    get_template_path,
    get_user_agent,
    hash_token,
    invitations_enabled,
    refresh_token_as_cookie,
    self_registration_enabled,
    set_refresh_token_cookie,
)


def _verified_redirect_url():
    """
    Where the browser lands once the address is confirmed and nothing else is due.

    Resolved on demand: the built-in page is only routed when ``EMAIL_VERIFIED_REDIRECT``
    is not configured, so reversing it eagerly breaks every installation that configured
    its own.

    Returns:
        str: URL configured through ``EMAIL_VERIFIED_REDIRECT``, or the built-in page,
        or ``None`` when neither is available.
    """
    configured = getattr(settings, EMAIL_VERIFIED_REDIRECT, None)
    if configured:
        return configured
    try:
        return reverse('jwt_allauth_email_verified')
    except NoReverseMatch:
        # The built-in page is only routed by the URLconf of ``jwt_allauth.registration``,
        # and a project is free to wire its endpoints by hand. That is a misconfiguration
        # -- ``jwt_allauth.checks`` reports it at startup -- but it surfaces on a link an
        # end user opens, so it must not be a 500 there. See ``_verified_response``.
        return None


def _verified_response(request):
    """
    Answer the browser that has just confirmed an address and needs nothing else.

    A redirect to the configured landing page, or the built-in page rendered in place
    when there is no URL to redirect to.

    Args:
        request (HttpRequest): Request being served.

    Returns:
        HttpResponse: Redirect, or the rendered confirmation page.
    """
    url = _verified_redirect_url()
    if url is None:
        return render(request, 'email/verified.html')
    return HttpResponseRedirect(url)


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
        if not refresh_token_as_cookie():
            # Installations that carry refresh tokens in the response body have no
            # body to carry it in here, and the URL is not an option: it would end up
            # in the browser history and in every log along the way.
            return

        refresh_token = RefreshToken.for_user(user, request, enabled=True)
        set_refresh_token_cookie(response, refresh_token)

    @staticmethod
    def _serves_invitation(token_entry) -> bool:
        """
        Whether this confirmation is an invitation being claimed.

        The purpose written with the token says so. It used to be inferred from the
        account having no usable password, which an account created through a social
        provider also satisfies -- so a provider's confirmation link could have been
        exchanged for the capability to set a password on it.

        The legacy shape is still honoured: invitations issued before the purpose
        existed carry ``EMAIL_CONFIRMATION``, and only closed registration could produce
        them, so under it a password-less account with one of those rows is an
        invitation in flight.
        """
        if token_entry.purpose == INVITATION:
            return True
        return not self_registration_enabled() and not token_entry.user.has_usable_password()

    def _confirm_without_capability(self, request):
        """
        Honour a confirmation that is not an invitation.

        ``None`` hands it back to the ordinary flow, which is what an installation with
        self-service sign-up wants. With registration closed there is no ordinary flow to
        hand it to -- these endpoints are the only ones routed -- so the address is
        confirmed here and the browser lands where any confirmation lands, without the
        password-set capability.
        """
        if self_registration_enabled():
            return None
        confirmation = self.get_object()
        confirmation.confirm(self.request)
        return _verified_response(request)

    def _claim_invitation(self, request, key):
        """
        Exchange an invitation's confirmation key for the password-set capability.

        Returns ``None`` when the key does not belong to an invitation, which is only
        possible while self-service sign-up is also open: the caller then carries on
        with the ordinary confirmation. With registration closed there is no such case,
        and a key with no invitation behind it is turned down as it always was.
        """
        # Ensure PASSWORD_SET_REDIRECT has been configured
        if self.form_url is None:
            raise NotImplementedError('`PASSWORD_SET_REDIRECT` must be configured in settings.py')

        # Check that the email confirmation token exists and is still within allauth's
        # confirmation window. Note: For an invitation, we allow multi-use
        # until password is set, but never beyond the expiration of the confirmation
        # itself: allauth's own expiry check is bypassed by the `except` clause below,
        # so the age of the key has to be enforced here as well.
        cutoff = timezone.now() - timedelta(
            days=allauth_app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS
        )
        # Keys are stored as digests. In-flight confirmations issued by a previous
        # version are still stored in plain text, so they are accepted as well until
        # they expire.
        token_entry = GenericTokenModel.objects.select_related('user').filter(
            token__in=(hash_token(key), key),
            purpose__in=(INVITATION, EMAIL_CONFIRMATION),
            created__gte=cutoff,
        ).first()
        if token_entry is None:
            if self_registration_enabled():
                return None
            return self._verification_failed(request)

        user = token_entry.user
        if not self._serves_invitation(token_entry):
            return self._confirm_without_capability(request)

        # A deactivated account gets no capability: login and refresh both refuse it,
        # and setting the password opens a session.
        if not user.is_active:
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

        # The password-set capability only makes sense for an invited account that has
        # not chosen a password yet. Issuing it for an account that already has one
        # would turn any confirmation link into a password reset link, bypassing the
        # reset flow and its throttling.
        #
        # Only the capability is withheld: the address is confirmed above either way,
        # which is what the link was sent for. Refusing that as well would leave the
        # account with no way forward -- login and the password reset flow both require
        # a verified address, so the link is the only thing that can hand it one -- and
        # it is not what closes the takeover. What was replayed is the capability.
        if user.has_usable_password():
            return _verified_response(request)

        # Create one-time access token to allow setting the password
        refresh_token = RefreshToken()
        refresh_token[FOR_USER] = user.id
        refresh_token[ONE_TIME_PERMISSION] = PASS_SET_ACCESS
        access_token = refresh_token.access_token

        response = HttpResponseRedirect(self.form_url)
        # The form this redirects to has to send a CSRF token back with the new
        # password, so the cookie holding it goes out together with the capability.
        ensure_csrf_cookie(request)
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

    @get_user_agent
    def get(self, request, *args, **kwargs):
        # An invitation is claimed here: the confirmation key is exchanged for the
        # one-time capability that lets the account set its first password. A key that
        # confirms an ordinary sign-up falls through to the flow below.
        if invitations_enabled():
            claimed = self._claim_invitation(request, kwargs['key'])
            if claimed is not None:
                return claimed

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

        response = _verified_response(request)
        if completes_signup:
            self._start_session(response, request, user)
        return response

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])
