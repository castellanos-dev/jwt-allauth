from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from jwt_allauth.constants import EMAIL_VERIFIED_REDIRECT
from jwt_allauth.registration.email_verification.views import VerifyEmailView
from jwt_allauth.registration.views import RegisterView
from jwt_allauth.utils import get_template_path

urlpatterns = [
    path('', RegisterView.as_view(), name='rest_register'),
]

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
