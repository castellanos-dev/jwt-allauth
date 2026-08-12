"""
A URLconf that wires the endpoints by hand, as a project is free to do.

It routes the e-mail confirmation link without routing the page the confirmation lands
on, which is the shape that used to answer ``500`` on a link an end user opens.
"""

from django.urls import path

from jwt_allauth.registration.email_verification.views import VerifyEmailView

urlpatterns = [
    path('registration/verification/<str:key>/', VerifyEmailView.as_view(), name='account_confirm_email'),
]
