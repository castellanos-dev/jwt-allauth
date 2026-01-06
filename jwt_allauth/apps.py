from importlib import reload

import allauth.app_settings
import rest_framework_simplejwt.settings
from django.apps import AppConfig


class JWTAllauthAppConfig(AppConfig):
    name = 'jwt_allauth'
    verbose_name = "JWT Allauth"
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from django.conf import settings
        from jwt_allauth import app_settings

        if not app_settings.ROTATE_REFRESH_TOKENS:
            raise ValueError('Refresh token rotation is compulsory.')
        if app_settings.BLACKLIST_AFTER_ROTATION:
            raise ValueError('Token blacklist is not supported.')

        if app_settings.ADMIN_MANAGED_REGISTRATION and app_settings.AUTHENTICATION_METHOD == 'phone':
            raise ValueError(
                "JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION=True is not compatible with "
                "JWT_ALLAUTH_AUTHENTICATION_METHOD='phone'. Use email for admin-managed invitations."
            )
        settings.EMAIL_VERIFICATION = getattr(settings, 'EMAIL_VERIFICATION', False)
        if app_settings.AUTHENTICATION_METHOD == 'email':
            settings.EMAIL_VERIFICATION = app_settings.IDENTIFIER_VERIFICATION
        if not hasattr(settings, 'ACCOUNT_ADAPTER'):
            settings.ACCOUNT_ADAPTER = 'jwt_allauth.adapter.JWTAllAuthAdapter'
        if not hasattr(settings, 'MFA_ADAPTER'):
            settings.MFA_ADAPTER = 'jwt_allauth.mfa.adapter.JWTAllAuthMFAAdapter'
        if hasattr(settings, 'ACCOUNT_LOGIN_METHODS') and settings.ACCOUNT_LOGIN_METHODS != {'email'}:
            raise ValueError('Only login email is supported.')
        settings.ACCOUNT_LOGIN_METHODS = {'email'}
        if (
                hasattr(settings, 'ACCOUNT_SIGNUP_FIELDS') and
                sorted(settings.ACCOUNT_SIGNUP_FIELDS) != ['email*', 'password1*', 'password2*']
        ):
            raise ValueError('Only login email is supported.')
        settings.ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']

        if not hasattr(settings, 'SITE_ID'):
            settings.SITE_ID = 1
        if not hasattr(settings, 'ACCOUNT_EMAIL_VERIFICATION'):
            settings.ACCOUNT_EMAIL_VERIFICATION = 'mandatory' if settings.EMAIL_VERIFICATION else 'none'
        if not hasattr(settings, 'UNIQUE_EMAIL'):
            settings.UNIQUE_EMAIL = True
        if not hasattr(settings, 'ACCOUNT_EMAIL_SUBJECT_PREFIX'):
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX = ''

        simple_jwt_settings = {
            "BLACKLIST_AFTER_ROTATION": False,
            "UPDATE_LAST_LOGIN": True,

            "ALGORITHM": "HS256",
            "SIGNING_KEY": app_settings.JWT_SECRET_KEY,
            "VERIFYING_KEY": "",
            "AUDIENCE": None,
            "ISSUER": None,
            "JSON_ENCODER": None,
            "JWK_URL": None,
            "LEEWAY": 0,

            "AUTH_HEADER_TYPES": ("Bearer",),
            "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
            "USER_ID_FIELD": "id",
            "USER_ID_CLAIM": "user_id",
            "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

            "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
            "TOKEN_TYPE_CLAIM": "token_type",
            "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
            "JTI_CLAIM": "jti",

            'ROTATE_REFRESH_TOKENS': True,
            'ACCESS_TOKEN_LIFETIME': app_settings.JWT_ACCESS_TOKEN_LIFETIME,
            'REFRESH_TOKEN_LIFETIME': app_settings.JWT_REFRESH_TOKEN_LIFETIME
        }
        if not hasattr(settings, 'SIMPLE_JWT'):
            settings.SIMPLE_JWT = simple_jwt_settings
        else:
            for k in simple_jwt_settings.keys():
                if k not in settings.SIMPLE_JWT:
                    settings.SIMPLE_JWT[k] = simple_jwt_settings[k]

        if not hasattr(settings, 'REST_FRAMEWORK'):
            settings.REST_FRAMEWORK = {
                'DEFAULT_AUTHENTICATION_CLASSES': (
                    'rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication',
                )
            }
        elif 'DEFAULT_AUTHENTICATION_CLASSES' not in settings.REST_FRAMEWORK:
            settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
                'rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication',
            )

        if not hasattr(settings, 'AUTHENTICATION_BACKENDS'):
            settings.AUTHENTICATION_BACKENDS = (
                # Needed to login by username in Django admin, regardless of `allauth`
                "django.contrib.auth.backends.ModelBackend",
                # `allauth` specific authentication methods, such as login by e-mail
                "allauth.account.auth_backends.AuthenticationBackend"
            )

        if "allauth.account.middleware.AccountMiddleware" not in settings.MIDDLEWARE:
            settings.MIDDLEWARE += ["allauth.account.middleware.AccountMiddleware"]

        reload(rest_framework_simplejwt.settings)
        reload(allauth.app_settings)
