from django.urls import path

from jwt_allauth.social.views import (
    SocialAccountDisconnectView,
    SocialAccountListView,
    SocialCodeConnectView,
    SocialCodeLoginView,
    SocialProviderListView,
    SocialTokenConnectView,
    SocialTokenLoginView,
)

# `accounts/` and `providers/` come first: without them a provider called "accounts"
# would be shadowed by nothing, but a provider id is free-form and the fixed paths have
# to win.
urlpatterns = [
    path('accounts/', SocialAccountListView.as_view(), name='jwt_allauth_social_accounts'),
    path('accounts/<int:pk>/', SocialAccountDisconnectView.as_view(), name='jwt_allauth_social_disconnect'),
    path('providers/', SocialProviderListView.as_view(), name='jwt_allauth_social_providers'),
    path('<str:provider>/token/', SocialTokenLoginView.as_view(), name='jwt_allauth_social_token_login'),
    path('<str:provider>/code/', SocialCodeLoginView.as_view(), name='jwt_allauth_social_code_login'),
    path(
        '<str:provider>/connect/token/',
        SocialTokenConnectView.as_view(),
        name='jwt_allauth_social_token_connect',
    ),
    path(
        '<str:provider>/connect/code/',
        SocialCodeConnectView.as_view(),
        name='jwt_allauth_social_code_connect',
    ),
]
