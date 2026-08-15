import warnings
from datetime import timedelta
from importlib import reload

import allauth.app_settings
import rest_framework_simplejwt.settings
from django.apps import AppConfig, apps
from django.core.exceptions import ImproperlyConfigured

#: The three states e-mail verification can be in, in allauth's vocabulary.
MANDATORY = 'mandatory'
OPTIONAL = 'optional'
NONE = 'none'
VERIFICATION_METHODS = (MANDATORY, OPTIONAL, NONE)


class JWTAllauthAppConfig(AppConfig):
    name = 'jwt_allauth'
    verbose_name = "JWT Allauth"
    default_auto_field = 'django.db.models.BigAutoField'

    @staticmethod
    def _resolve_email_verification(settings):
        """
        Settle on one verification method and make both settings say it.

        ``EMAIL_VERIFICATION`` is this library's setting and the authoritative one. It
        accepts the three methods by name -- ``'mandatory'``, ``'optional'``,
        ``'none'`` -- as well as the booleans it has always taken, where ``True`` means
        ``'mandatory'`` and ``False`` means ``'none'``.

        allauth's ``ACCOUNT_EMAIL_VERIFICATION`` is derived from it, and a project may
        still declare it instead: that is how ``'optional'`` was reachable before
        ``EMAIL_VERIFICATION`` could name it, and it keeps working. What it cannot do is
        contradict a method spelled out here.

        The two used to govern different halves of the feature -- ``EMAIL_VERIFICATION``
        the routing of the confirmation URL and the auto-confirmation at sign-up,
        allauth's whether the mail is sent -- with nothing to keep them in step, so a
        disagreeing pair produced a state nobody designed. They are reconciled here,
        once, and everything downstream reads a boolean ``EMAIL_VERIFICATION`` and a
        method that agrees with it.

        Args:
            settings: Django settings module being configured.

        Returns:
            str: The resolved method, one of :data:`VERIFICATION_METHODS`.

        Raises:
            ImproperlyConfigured: if ``EMAIL_VERIFICATION`` names something that is not
                a verification method.
        """
        configured = getattr(settings, 'EMAIL_VERIFICATION', False)
        declared = getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION', None)
        if declared is not None:
            declared = str(declared).lower()

        if isinstance(configured, str):
            method = configured.lower()
            if method not in VERIFICATION_METHODS:
                raise ImproperlyConfigured(
                    f"jwt-allauth: EMAIL_VERIFICATION must be one of {VERIFICATION_METHODS}, "
                    f"or a boolean, not {configured!r}."
                )
            if declared is not None and declared != method:
                warnings.warn(
                    f"jwt-allauth: EMAIL_VERIFICATION = {configured!r} and "
                    f"ACCOUNT_EMAIL_VERIFICATION = {declared!r} disagree. "
                    f"EMAIL_VERIFICATION is this library's own setting and wins; drop "
                    f"ACCOUNT_EMAIL_VERIFICATION, which is derived from it.",
                    stacklevel=2,
                )
            return method

        if not configured:
            # The boolean is off, which has always meant that addresses are confirmed at
            # sign-up and no link is ever sent. A method declared next to it never took
            # effect, so honouring it now would turn verification on under a deployment
            # that has been running without it.
            if declared is not None and declared != NONE:
                warnings.warn(
                    f"jwt-allauth: ACCOUNT_EMAIL_VERIFICATION = {declared!r} is ignored while "
                    f"EMAIL_VERIFICATION is False -- addresses are confirmed at sign-up and no "
                    f"confirmation link is sent. Set EMAIL_VERIFICATION = {declared!r} to get "
                    f"the verification you asked for.",
                    stacklevel=2,
                )
            return NONE

        if declared is None:
            return MANDATORY
        if declared == NONE:
            # Nothing could ever come of this pair: the confirmation URL is routed and
            # addresses are left unconfirmed, but allauth sends no link to confirm them
            # with, so every account stays unverified for good. Resolved to the method
            # that was asked for rather than left half-applied.
            warnings.warn(
                "jwt-allauth: EMAIL_VERIFICATION = True with ACCOUNT_EMAIL_VERIFICATION = 'none' "
                "never delivers a confirmation link, so no address could ever be verified. "
                "Treating it as 'none'; set EMAIL_VERIFICATION = 'mandatory' or 'optional' to "
                "verify addresses.",
                stacklevel=2,
            )
            return NONE
        if declared not in VERIFICATION_METHODS:
            raise ImproperlyConfigured(
                f"jwt-allauth: ACCOUNT_EMAIL_VERIFICATION must be one of {VERIFICATION_METHODS}, "
                f"not {declared!r}."
            )
        return declared

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

        # Importing the module registers the checks it declares.
        from jwt_allauth import checks  # noqa: F401

        self._reject_unsupported(settings)
        self._default_allauth(settings)
        self._default_simplejwt(settings)
        self._default_rest_framework(settings)

        reload(rest_framework_simplejwt.settings)
        reload(allauth.app_settings)

    @staticmethod
    def _reject_unsupported(settings):
        """
        Refuse a configuration this library cannot honour, before anything reads it.

        These are not defaults being filled in: each one describes a session model that
        contradicts this library's -- rotation is what makes the whitelist work, and a
        blacklist is what it exists instead of.
        """
        if not getattr(settings, 'ROTATE_REFRESH_TOKENS', True):
            raise ValueError('Refresh token rotation is compulsory.')
        if getattr(settings, 'BLACKLIST_AFTER_ROTATION', False):
            raise ValueError('Token blacklist is not supported.')

        session_lifetime = getattr(settings, 'JWT_ALLAUTH_SESSION_LIFETIME', None)
        if session_lifetime is not None and not isinstance(session_lifetime, timedelta):
            raise ValueError('JWT_ALLAUTH_SESSION_LIFETIME must be a datetime.timedelta or None.')

    def _default_allauth(self, settings):
        """Fill in what allauth needs, leaving anything the project declared alone."""
        # Both settings end up saying the same thing: a boolean EMAIL_VERIFICATION for
        # everything that only asks whether the feature is on -- the confirmation URL,
        # the auto-confirmation at sign-up -- and the method itself in allauth's setting.
        verification_method = self._resolve_email_verification(settings)
        settings.ACCOUNT_EMAIL_VERIFICATION = verification_method
        settings.EMAIL_VERIFICATION = verification_method != NONE

        if not hasattr(settings, 'ACCOUNT_ADAPTER'):
            settings.ACCOUNT_ADAPTER = 'jwt_allauth.adapter.JWTAllAuthAdapter'
        if not hasattr(settings, 'MFA_ADAPTER'):
            settings.MFA_ADAPTER = 'jwt_allauth.mfa.adapter.JWTAllAuthMFAAdapter'
        if apps.is_installed('allauth.socialaccount') and not hasattr(settings, 'SOCIALACCOUNT_ADAPTER'):
            settings.SOCIALACCOUNT_ADAPTER = 'jwt_allauth.social.adapter.JWTAllAuthSocialAccountAdapter'
        # The two guards below are about the local sign-up form, which the social flow
        # never renders: `save_user` takes its `form is None` branch, so an account
        # created through a provider needs no password field. What they do reach is
        # `SOCIALACCOUNT_EMAIL_REQUIRED`, which allauth derives from ACCOUNT_SIGNUP_FIELDS
        # and which comes out `True` -- which is what this library wants anyway.
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
        if not hasattr(settings, 'UNIQUE_EMAIL'):
            settings.UNIQUE_EMAIL = True
        if not hasattr(settings, 'ACCOUNT_EMAIL_SUBJECT_PREFIX'):
            settings.ACCOUNT_EMAIL_SUBJECT_PREFIX = ''

    def _default_simplejwt(self, settings):
        """Fill in ``SIMPLE_JWT``, key by key, so a partial declaration still works."""
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

    @staticmethod
    def _default_rest_framework(settings):
        """Wire the authentication class, the backends and the middleware allauth needs."""
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
