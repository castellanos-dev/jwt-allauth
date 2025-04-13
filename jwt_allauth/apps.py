from datetime import timedelta
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

        if not getattr(settings, 'ROTATE_REFRESH_TOKENS', True):
            raise ValueError('Refresh token rotation is compulsory.')
        if getattr(settings, 'BLACKLIST_AFTER_ROTATION', False):
            raise ValueError('Token blacklist is not supported.')

        settings.EMAIL_VERIFICATION = getattr(settings, 'EMAIL_VERIFICATION', False)
        if not hasattr(settings, 'ACCOUNT_ADAPTER'):
            settings.ACCOUNT_ADAPTER = 'jwt_allauth.adapter.JWTAllAuthAdapter'
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
            "SIGNING_KEY": getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY),
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
            'ACCESS_TOKEN_LIFETIME': getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', timedelta(minutes=30)),
            'REFRESH_TOKEN_LIFETIME': getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', timedelta(days=90))
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
