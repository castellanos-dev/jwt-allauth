from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from jwt_allauth.constants import EMAIL_VERIFIED_REDIRECT, PASSWORD_SET_REDIRECT
from jwt_allauth.registration.email_verification.views import VerifyEmailView
from jwt_allauth.registration.views import RegisterView, UserRegisterView
from jwt_allauth.password_reset.views import SetPasswordView, DefaultSetPasswordView

urlpatterns = []


if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
    urlpatterns.extend([
        path('user-register/', UserRegisterView.as_view(), name='rest_user_register'),
        path('set-password/', SetPasswordView.as_view(), name='rest_set_password'),
        path('verification/<str:key>/', VerifyEmailView.as_view(), name='account_confirm_email'),
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

else:
    urlpatterns.append(path('', RegisterView.as_view(), name='rest_register'))

    if getattr(settings, 'EMAIL_VERIFICATION', False):
        urlpatterns.extend([
            path('verification/<str:key>/', VerifyEmailView.as_view(), name='account_confirm_email'),

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
            path('account_email_verification_sent/', TemplateView.as_view(), name='account_email_verification_sent'),
        ])

        if getattr(settings, EMAIL_VERIFIED_REDIRECT, None) is None:
            urlpatterns.append(
                path('verified/', TemplateView.as_view(
                    template_name='email/verified.html'), name='jwt_allauth_email_verified'),
            )
