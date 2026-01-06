from django.conf import settings
from datetime import timedelta
import warnings

from django.utils.translation import gettext_lazy as _
from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE
from jwt_allauth._importing import import_callable


def _get_serializer(serializer_key: str, default_path: str):
    serializers = getattr(settings, 'JWT_ALLAUTH_SERIALIZERS', {})
    return import_callable(serializers.get(serializer_key, default_path))


def _default_path_by_authentication_method(phone_path: str, email_path: str) -> str:
    authentication_method = getattr(settings, 'JWT_ALLAUTH_AUTHENTICATION_METHOD', 'email')
    return phone_path if authentication_method == 'phone' else email_path


def __getattr__(name: str):
    if name == 'IDENTIFIER_VERIFICATION':
        if hasattr(settings, 'JWT_ALLAUTH_IDENTIFIER_VERIFICATION'):
            value = getattr(settings, 'JWT_ALLAUTH_IDENTIFIER_VERIFICATION')
            if value is not None:
                return value

        if hasattr(settings, 'EMAIL_VERIFICATION'):
            warnings.warn(
                'EMAIL_VERIFICATION is deprecated and will be removed in a future release. '
                'Please use JWT_ALLAUTH_IDENTIFIER_VERIFICATION instead.',
                DeprecationWarning,
                stacklevel=2,
            )
        return getattr(settings, 'EMAIL_VERIFICATION', False)

    if name == 'EMAIL_VERIFICATION':
        warnings.warn(
            'EMAIL_VERIFICATION is deprecated and will be removed in a future release. '
            'Please use JWT_ALLAUTH_IDENTIFIER_VERIFICATION instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        return __getattr__('IDENTIFIER_VERIFICATION')

    if name == 'UserDetailsSerializer':
        return _get_serializer(
            'USER_DETAILS_SERIALIZER',
            'jwt_allauth.user_details.serializers.UserDetailsSerializer',
        )
    if name == 'LoginSerializer':
        default_path = _default_path_by_authentication_method(
            phone_path='jwt_allauth.login.serializers.PhoneLoginSerializer',
            email_path='jwt_allauth.login.serializers.EmailLoginSerializer',
        )
        return _get_serializer('LOGIN_SERIALIZER', default_path)
    if name == 'PasswordResetSerializer':
        return _get_serializer(
            'PASSWORD_RESET_SERIALIZER',
            'jwt_allauth.password_reset.serializers.PasswordResetSerializer',
        )
    if name == 'PasswordChangeSerializer':
        return _get_serializer(
            'PASSWORD_CHANGE_SERIALIZER',
            'jwt_allauth.password_change.serializers.PasswordChangeSerializer',
        )
    if name == 'RegisterSerializer':
        default_path = _default_path_by_authentication_method(
            phone_path='jwt_allauth.registration.serializers.PhoneRegisterSerializer',
            email_path='jwt_allauth.registration.serializers.EmailRegisterSerializer',
        )
        return _get_serializer('REGISTER_SERIALIZER', default_path)

    if name in _SETTING_DEFAULTS:
        setting_name, default = _SETTING_DEFAULTS[name]
        if default is _REQUIRED:
            return getattr(settings, setting_name)
        if callable(default):
            default = default()
        return getattr(settings, setting_name, default)

    raise AttributeError(name)


_REQUIRED = object()


def _default_registration_allowed_roles():
    return [STAFF_CODE, SUPER_USER_CODE]


def _default_sms_opts():
    return {}


def _default_user_attributes():
    return {}


def _default_refresh_cookie_secure():
    return not settings.DEBUG


def _default_password_reset_cookie_secure():
    return not settings.DEBUG


def _default_password_set_cookie_secure():
    return not settings.DEBUG


def _default_jwt_secret_key():
    return settings.SECRET_KEY


_SETTING_DEFAULTS = {
    'AUTHENTICATION_METHOD': ('JWT_ALLAUTH_AUTHENTICATION_METHOD', 'email'),
    'ADMIN_MANAGED_REGISTRATION': ('JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False),
    'REGISTRATION_ALLOWED_ROLES': ('JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES', _default_registration_allowed_roles),
    'REGISTER_PERMISSION_CLASSES': ('JWT_ALLAUTH_REGISTER_PERMISSION_CLASSES', tuple()),

    # Phone & SMS
    'PHONE_CONFIRMATION_EXPIRE_SECONDS': ('JWT_ALLAUTH_PHONE_CONFIRMATION_EXPIRE_SECONDS', 300),
    'SMS_VERIFICATION_MESSAGE': ('JWT_ALLAUTH_SMS_VERIFICATION_MESSAGE', _('Your verification code is: {code}')),
    'SMS_BACKEND': ('JWT_ALLAUTH_SMS_BACKEND', 'jwt_allauth.sms.backend.ConsoleSMSBackend'),
    'SMS_OPTS': ('JWT_ALLAUTH_SMS_OPTS', _default_sms_opts),

    # MFA
    'MFA_TOTP_MODE': ('JWT_ALLAUTH_MFA_TOTP_MODE', 'disabled'),
    'TOTP_ISSUER': ('JWT_ALLAUTH_TOTP_ISSUER', 'JWT-Allauth'),

    # Cookies
    'REFRESH_TOKEN_AS_COOKIE': ('JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE', True),
    'REFRESH_TOKEN_COOKIE_HTTP_ONLY': ('JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_HTTP_ONLY', True),
    'REFRESH_TOKEN_COOKIE_SECURE': ('JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SECURE', _default_refresh_cookie_secure),
    'REFRESH_TOKEN_COOKIE_SAME_SITE': ('JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SAME_SITE', 'Lax'),
    'REFRESH_TOKEN_COOKIE_MAX_AGE': ('JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_MAX_AGE', None),

    'PASSWORD_RESET_COOKIE_HTTP_ONLY': ('PASSWORD_RESET_COOKIE_HTTP_ONLY', True),
    'PASSWORD_RESET_COOKIE_SECURE': ('PASSWORD_RESET_COOKIE_SECURE', _default_password_reset_cookie_secure),
    'PASSWORD_RESET_COOKIE_SAME_SITE': ('PASSWORD_RESET_COOKIE_SAME_SITE', 'Lax'),
    'PASSWORD_RESET_COOKIE_MAX_AGE': ('PASSWORD_RESET_COOKIE_MAX_AGE', 3600),

    'PASSWORD_SET_COOKIE_HTTP_ONLY': ('PASSWORD_SET_COOKIE_HTTP_ONLY', True),
    'PASSWORD_SET_COOKIE_SECURE': ('PASSWORD_SET_COOKIE_SECURE', _default_password_set_cookie_secure),
    'PASSWORD_SET_COOKIE_SAME_SITE': ('PASSWORD_SET_COOKIE_SAME_SITE', 'Lax'),
    'PASSWORD_SET_COOKIE_MAX_AGE': ('PASSWORD_SET_COOKIE_MAX_AGE', 3600 * 24),

    # Redirects
    'PASSWORD_RESET_REDIRECT': ('PASSWORD_RESET_REDIRECT', None),
    'PASSWORD_SET_REDIRECT': ('PASSWORD_SET_REDIRECT', '/registration/set-password/default/'),

    # Other
    'LOGOUT_ON_PASSWORD_CHANGE': ('LOGOUT_ON_PASSWORD_CHANGE', True),
    'OLD_PASSWORD_FIELD_ENABLED': ('OLD_PASSWORD_FIELD_ENABLED', True),
    'COLLECT_USER_AGENT': ('JWT_ALLAUTH_COLLECT_USER_AGENT', False),
    'USER_ATTRIBUTES': ('JWT_ALLAUTH_USER_ATTRIBUTES', _default_user_attributes),
    'REFRESH_TOKEN_CLASS': ('JWT_ALLAUTH_REFRESH_TOKEN', 'jwt_allauth.tokens.tokens.RefreshToken'),

    'REST_AUTH_TOKEN_MODEL': ('REST_AUTH_TOKEN_MODEL', 'rest_framework.authtoken.models.Token'),

    # JWT Settings defaults for apps.py
    'JWT_SECRET_KEY': ('JWT_SECRET_KEY', _default_jwt_secret_key),
    'JWT_ACCESS_TOKEN_LIFETIME': ('JWT_ACCESS_TOKEN_LIFETIME', timedelta(minutes=30)),
    'JWT_REFRESH_TOKEN_LIFETIME': ('JWT_REFRESH_TOKEN_LIFETIME', timedelta(days=90)),

    # Django & Allauth Settings
    'DEFAULT_FROM_EMAIL': ('DEFAULT_FROM_EMAIL', _REQUIRED),
    'ACCOUNT_AUTHENTICATION_METHOD': ('ACCOUNT_AUTHENTICATION_METHOD', 'email'),
    'IDENTIFIER_VERIFICATION': ('JWT_ALLAUTH_IDENTIFIER_VERIFICATION', None),
    'EMAIL_VERIFICATION': ('EMAIL_VERIFICATION', False),
    'ROTATE_REFRESH_TOKENS': ('ROTATE_REFRESH_TOKENS', True),
    'BLACKLIST_AFTER_ROTATION': ('BLACKLIST_AFTER_ROTATION', False),
}


def __dir__():
    return sorted(set(list(globals().keys()) + list(_SETTING_DEFAULTS.keys())))
