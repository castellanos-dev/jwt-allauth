import warnings
from datetime import timedelta
from importlib import reload

import allauth.app_settings
import rest_framework_simplejwt.settings
from django.apps import AppConfig


class JWTAllauthAppConfig(AppConfig):
    name = 'jwt_allauth'
    verbose_name = "JWT Allauth"
    default_auto_field = 'django.db.models.BigAutoField'

    @staticmethod
    def _get_signing_key(settings):
        if hasattr(settings, 'JWT_ALLAUTH_SECRET_KEY'):
            return settings.JWT_ALLAUTH_SECRET_KEY
        if hasattr(settings, 'JWT_SECRET_KEY'):
            warnings.warn(
                "jwt-allauth: JWT_SECRET_KEY is deprecated. Use JWT_ALLAUTH_SECRET_KEY instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return settings.JWT_SECRET_KEY
        if not settings.DEBUG:
            warnings.warn(
                "jwt-allauth: JWT_ALLAUTH_SECRET_KEY is not set. Falling back to SECRET_KEY for JWT signing. "
                "This is insecure for production — a leak of SECRET_KEY (e.g. via CSRF or session "
                "internals) would compromise all JWTs. Set JWT_ALLAUTH_SECRET_KEY to a dedicated secret.",
                stacklevel=2,
            )
        return settings.SECRET_KEY

    @staticmethod
    def _get_setting(settings, new_name, old_name, default):
        """Read a setting preferring the new JWT_ALLAUTH_* name, falling back to the deprecated name."""
        if hasattr(settings, new_name):
            return getattr(settings, new_name)
        if hasattr(settings, old_name):
            warnings.warn(
                f"jwt-allauth: {old_name} is deprecated. Use {new_name} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return getattr(settings, old_name)
        return default

    def ready(self):
        from django.conf import settings

        if not getattr(settings, 'ROTATE_REFRESH_TOKENS', True):
            raise ValueError('Refresh token rotation is compulsory.')
        if getattr(settings, 'BLACKLIST_AFTER_ROTATION', False):
            raise ValueError('Token blacklist is not supported.')

        session_lifetime = getattr(settings, 'JWT_ALLAUTH_SESSION_LIFETIME', None)
        if session_lifetime is not None and not isinstance(session_lifetime, timedelta):
            raise ValueError('JWT_ALLAUTH_SESSION_LIFETIME must be a datetime.timedelta or None.')

        settings.EMAIL_VERIFICATION = getattr(settings, 'EMAIL_VERIFICATION', False)
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
            "SIGNING_KEY": self._get_signing_key(settings),
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
            'ACCESS_TOKEN_LIFETIME': self._get_setting(
                settings, 'JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME', 'JWT_ACCESS_TOKEN_LIFETIME', timedelta(minutes=30)),
            'REFRESH_TOKEN_LIFETIME': self._get_setting(
                settings, 'JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME', 'JWT_REFRESH_TOKEN_LIFETIME', timedelta(days=14))
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
                    'jwt_allauth.authentication.JWTAllAuthAuthentication',
                )
            }
        elif 'DEFAULT_AUTHENTICATION_CLASSES' not in settings.REST_FRAMEWORK:
            settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
                'jwt_allauth.authentication.JWTAllAuthAuthentication',
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
