from django.urls import path

from .views import (
    MFASetupView,
    MFAActivateView,
    MFAVerifyView,
    MFAVerifyRecoveryView,
    MFADeactivateView,
    MFAListAuthenticatorsView,
)

urlpatterns = [
    path("setup/", MFASetupView.as_view(), name="jwt_allauth_mfa_setup"),
    path("activate/", MFAActivateView.as_view(), name="jwt_allauth_mfa_activate"),
    path("verify/", MFAVerifyView.as_view(), name="jwt_allauth_mfa_verify"),
    path("verify-recovery/", MFAVerifyRecoveryView.as_view(), name="jwt_allauth_mfa_verify_recovery"),
    path("deactivate/", MFADeactivateView.as_view(), name="jwt_allauth_mfa_deactivate"),
    path("authenticators/", MFAListAuthenticatorsView.as_view(), name="jwt_allauth_mfa_authenticators"),
]
