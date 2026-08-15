from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from jwt_allauth.constants import EMAIL_VERIFIED_REDIRECT, PASSWORD_SET_REDIRECT
from jwt_allauth.registration.email_verification.views import VerifyEmailView
from jwt_allauth.registration.views import RegisterView, UserRegisterView
from jwt_allauth.password_reset.views import SetPasswordView, DefaultSetPasswordView
from jwt_allauth.utils import invitations_enabled, self_registration_enabled, verification_enabled

# The two ways in are routed independently, because they are independent questions.
# Invitations can be added to a project that keeps its public sign-up, and
# `JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION` -- which is invitations *and* no public
# sign-up -- comes out of the same two flags.
urlpatterns = []


if invitations_enabled():
    urlpatterns.extend([
        path('user-register/', UserRegisterView.as_view(), name='rest_user_register'),
        path('set-password/', SetPasswordView.as_view(), name='rest_set_password'),
    ])

    # Only register the built-in HTML UI if no custom PASSWORD_SET_REDIRECT is configured
    if getattr(settings, PASSWORD_SET_REDIRECT, None) is None:
        urlpatterns.append(
            path(
                'set-password/default/',
                DefaultSetPasswordView.as_view(),
                name='jwt_allauth_default_set_password',
            )
        )

if self_registration_enabled():
    urlpatterns.append(path('', RegisterView.as_view(), name='rest_register'))

# The confirmation link carries an invitation and confirms a sign-up alike, so it is
# routed for either.
if invitations_enabled() or verification_enabled():
    urlpatterns.append(
        path('verification/<str:key>/', VerifyEmailView.as_view(), name='account_confirm_email'),
    )

    # An account that already has a password is only confirmed, never handed a
    # password-set capability, and lands on the same page as any other verification.
    if getattr(settings, EMAIL_VERIFIED_REDIRECT, None) is None:
        urlpatterns.append(
            path('verified/', TemplateView.as_view(
                template_name='email/verified.html'), name='jwt_allauth_email_verified'),
        )

if self_registration_enabled() and verification_enabled():
    # This url is used by django-allauth and empty TemplateView is
    # defined just to allow reverse() call inside app, for example when email
    # with verification link is being sent, then it's required to render email
    # content.

    # account_confirm_email - You should override this view to handle it in
    # your API client somehow and then, send post to /verify-email/ endpoint
    # with proper key.
    # If you don't want to use API on that step, then just use ConfirmEmailView
    # view from:
    # django-allauth https://github.com/pennersr/django-allauth/blob/master/allauth/account/views.py
    urlpatterns.append(
        path('account_email_verification_sent/', TemplateView.as_view(), name='account_email_verification_sent'),
    )
