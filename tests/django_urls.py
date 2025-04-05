# Moved in Django 1.8 from django to tests/auth_tests/urls.py

from django.urls import path, re_path
from django.contrib.auth import views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.urls import urlpatterns


# special urls for auth test cases
urlpatterns += [
    path('logout/custom_query/', views.LogoutView.as_view(), dict(redirect_field_name='follow')),
    path('logout/next_page/', views.LogoutView.as_view(), dict(next_page='/somewhere/')),
    path('logout/next_page/named/', views.LogoutView.as_view(), dict(next_page='password_reset')),
    path('password_reset_from_email/', views.PasswordResetView.as_view(), dict(from_email='staffmember@example.com')),
    path('password_reset/custom_redirect/', views.PasswordResetView.as_view(), dict(post_reset_redirect='/custom/')),
    path(
        'password_reset/custom_redirect/named/',
        views.PasswordResetView.as_view(),
        dict(post_reset_redirect='password_reset')
    ),
    path(
        'password_reset/html_email_template/',
        views.PasswordResetView.as_view(),
        dict(html_email_template_name='registration/html_password_reset_email.html')
    ),
    re_path(
        r'^reset/custom/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.PasswordResetConfirmView.as_view(),
        dict(post_reset_redirect='/custom/')
    ),
    re_path(
        r'^reset/custom/named/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.PasswordResetConfirmView.as_view(),
        dict(post_reset_redirect='password_reset')
    ),
    path('password_change/custom/', views.PasswordChangeView.as_view(), dict(post_change_redirect='/custom/')),
    path(
        'password_change/custom/named/',
        views.PasswordChangeView.as_view(),
        dict(post_change_redirect='password_reset')
    ),
    path('admin_password_reset/', views.PasswordResetView.as_view(), dict(is_admin_site=True)),
    path('login_required/', login_required(views.PasswordResetView.as_view())),
    path('login_required_login_url/', login_required(views.PasswordResetView.as_view(), login_url='/somewhere/')),
]
