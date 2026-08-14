from django.apps import apps
from django.urls import path, include
from django.conf import settings
from django.views.generic import TemplateView

from jwt_allauth.login.views import LoginView
from jwt_allauth.logout.views import LogoutView, LogoutAllView
from jwt_allauth.password_change.views import PasswordChangeView
from jwt_allauth.password_reset.views import PasswordResetView, PasswordResetConfirmView, ResetPasswordView, DefaultPasswordResetView
from jwt_allauth.registration import urls as registration_urls
from jwt_allauth.token_refresh.views import TokenRefreshView
from jwt_allauth.mfa import urls as mfa_urls
from jwt_allauth.user_details.views import UserDetailsView


urlpatterns = [
    # URLs that do not require a session or valid token
    path('password/reset/', PasswordResetView.as_view(), name='rest_password_reset'),
    path('password/reset/set-new/', ResetPasswordView.as_view(), name='rest_password_reset_set_new'),
    path(
        'password/reset/confirm/<str:uidb64>/<str:token>/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),
    path('login/', LoginView.as_view(), name='rest_login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # URLs that require a user to be logged in with a valid session / token.
    path('logout/', LogoutView.as_view(), name='rest_logout'),
    path('logout-all/', LogoutAllView.as_view(), name='rest_logout_all'),
    path('user/', UserDetailsView.as_view(), name='rest_user_details'),
    path('password/change/', PasswordChangeView.as_view(), name='rest_password_change'),
    # Registration urls
    path('registration/', include(registration_urls)),
    # MFA urls
    path('mfa/', include(mfa_urls)),
]

# Social urls. Routed only when the project installs allauth's socialaccount app, whose
# HTTP stack (`requests`, `pyjwt[crypto]`) sits behind an extra: importing the views
# unconditionally would make that extra a hard dependency of every installation.
#
# Having the app installed is not enough, because the two can come apart: `startproject`
# has always written `allauth.socialaccount` into INSTALLED_APPS, and until these
# endpoints existed nothing imported its HTTP stack -- so a project generated before
# them can be running happily today without the extra. Raising on it at import time
# would break that project on upgrade over a feature it never asked for.
# `jwt_allauth.checks.check_social_providers` reports the shortfall instead.
if apps.is_installed('allauth.socialaccount'):
    try:
        from jwt_allauth.social import urls as social_urls
    except ImportError:  # pragma: no cover - exercised by installations without the extra
        pass
    else:
        urlpatterns.append(path('social/', include(social_urls)))

if getattr(settings, 'PASSWORD_RESET_REDIRECT', None) is None:
    urlpatterns.append(
        path('password/reset/default/', DefaultPasswordResetView.as_view(), name='default_password_reset')
    )
    urlpatterns.append(
        path('password/reset/complete/', TemplateView.as_view(
            template_name='password/reset_complete.html'
        ), name='jwt_allauth_password_reset_complete'),
    )
