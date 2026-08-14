"""
Startup checks for configurations that would otherwise only fail in production.

Registered from :meth:`jwt_allauth.apps.JWTAllauthAppConfig.ready`, and run by
``manage.py check``, ``runserver`` and the deployment checks.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

from django.apps import apps
from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.urls import NoReverseMatch, reverse

from jwt_allauth.constants import EMAIL_VERIFIED_REDIRECT
from jwt_allauth.roles import ROLE_FIELD, STAFF_CODE, SUPER_USER_CODE

#: Identifier of the check reported when the confirmation flow has nowhere to land.
VERIFIED_REDIRECT_ID = 'jwt_allauth.W001'

#: Identifier of the check reported when the role field holds something no token can carry.
ROLE_FIELD_RELATION_ID = 'jwt_allauth.E001'

#: Identifier of the check reported when the role field cannot hold the built-in role codes.
ROLE_FIELD_TYPE_ID = 'jwt_allauth.W002'

#: Identifier of the check reported when an upstream is newer than anything this release saw.
UNTESTED_UPSTREAM_ID = 'jwt_allauth.W003'

#: Identifier of the check reported when the social endpoints are routed with no provider set up.
SOCIAL_NO_PROVIDERS_ID = 'jwt_allauth.W004'

#: Identifier of the check reported when allauth's own e-mail authentication is declared.
SOCIAL_EMAIL_AUTHENTICATION_ID = 'jwt_allauth.W005'

#: Highest major of each upstream this release was tested against, and what is at stake.
#:
#: These two are not ordinary dependencies. The library subclasses simplejwt's token and
#: authentication classes and rewrites its settings at startup, and it reaches into
#: ``allauth.mfa``'s internal TOTP and recovery-code helpers -- modules under a package
#: named ``internal``, which is allauth's way of saying they may move. A major release of
#: either can therefore break this library in ways its own version number says nothing
#: about. **Bump these on every release that tests against a new major.**
TESTED_UPSTREAM_MAJORS = {
    'django-allauth': 65,
    'djangorestframework-simplejwt': 5,
}


def _reverses(name, **kwargs):
    try:
        reverse(name, kwargs=kwargs)
    except NoReverseMatch:
        return False
    return True


@register(Tags.urls)
def check_verified_redirect(app_configs, **kwargs):
    """
    Report a confirmation flow that is routed but has no page to land on.

    ``EMAIL_VERIFIED_REDIRECT`` is where the browser goes once an address is confirmed;
    with it unset the flow falls back to the built-in page, which is only routed by the
    URLconf of ``jwt_allauth.registration``. A project that wires its endpoints by hand
    can therefore route the confirmation link without routing its destination, and that
    only shows up when an end user opens the link. The page is rendered in place when it
    happens, so this is a warning rather than an error, but the landing page is the
    project's to choose.
    """
    if not _reverses('account_confirm_email', key='key'):
        # The confirmation link is not routed at all: nothing to land on either.
        return []
    if getattr(settings, EMAIL_VERIFIED_REDIRECT, None):
        return []
    if _reverses('jwt_allauth_email_verified'):
        return []
    return [
        Warning(
            'The e-mail confirmation link is routed, but there is nowhere for it to land.',
            hint=(
                f"Set {EMAIL_VERIFIED_REDIRECT} to the page the browser should land on once an "
                f"address is confirmed, or route 'jwt_allauth_email_verified' by including "
                f"jwt_allauth.registration.urls. Until then the confirmation renders the "
                f"built-in page in place."
            ),
            id=VERIFIED_REDIRECT_ID,
        )
    ]


@register(Tags.urls)
def check_social_providers(app_configs, **kwargs):
    """
    Report social endpoints that cannot serve a request as configured.

    Two ways to get there, and both answer ``404`` to everything, which reads as a bug
    in this library rather than as a missing piece of configuration:

        - ``allauth.socialaccount`` is installed but its HTTP stack is not, so the views
          were never routed. ``jwt-allauth startproject`` has always written the app into
          ``INSTALLED_APPS``, so a project can arrive here without ever having asked for
          social login.
        - The endpoints are routed but no provider app is declared in settings. A warning
          rather than an error, and deliberately so: apps registered in the database are
          a supported setup, and a startup check must not query the database to find out.
    """
    if not _reverses('jwt_allauth_social_token_login', provider='google'):
        if not apps.is_installed('allauth.socialaccount'):
            return []
        try:
            import jwt_allauth.social.urls  # noqa: F401
        except ImportError:
            return [
                Warning(
                    "'allauth.socialaccount' is installed, but its dependencies are not, "
                    'so the social endpoints are not routed.',
                    hint=(
                        "Install them with `pip install django-jwt-allauth[social]`, or drop "
                        "'allauth.socialaccount' from INSTALLED_APPS if the project does not "
                        'use social login.'
                    ),
                    id=SOCIAL_NO_PROVIDERS_ID,
                )
            ]
        return []
    providers = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}) or {}
    if any(cfg.get('APP') or cfg.get('APPS') for cfg in providers.values() if isinstance(cfg, dict)):
        return []
    return [
        Warning(
            'The social endpoints are routed, but no provider app is configured in settings.',
            hint=(
                "Add the client id and secret under SOCIALACCOUNT_PROVIDERS, e.g. "
                "{'google': {'APPS': [{'client_id': '...', 'secret': '...'}]}}, or register "
                "the app in the database through the admin. Until then every social "
                "endpoint answers 404."
            ),
            id=SOCIAL_NO_PROVIDERS_ID,
        )
    ]


@register(Tags.security)
def check_social_email_authentication(app_configs, **kwargs):
    """
    Report ``SOCIALACCOUNT_EMAIL_AUTHENTICATION``, which these endpoints do not read.

    allauth's setting governs its own views, and its implementation wipes the local
    password whenever it matches an account by address. This library decides the same
    question itself -- and keeps the password when the address was already confirmed --
    so a project that sets allauth's flag expecting it to change these endpoints has
    configured nothing at all.
    """
    if not hasattr(settings, 'SOCIALACCOUNT_EMAIL_AUTHENTICATION'):
        return []
    if not _reverses('jwt_allauth_social_token_login', provider='google'):
        return []
    return [
        Warning(
            'SOCIALACCOUNT_EMAIL_AUTHENTICATION does not apply to the jwt-allauth social endpoints.',
            hint=(
                "Use JWT_ALLAUTH_SOCIAL_EMAIL_LINKING instead: True (the default) to link a "
                "provider-verified address to the account that already holds it, False to "
                "refuse, or a list of provider ids to allow it for some providers only."
            ),
            id=SOCIAL_EMAIL_AUTHENTICATION_ID,
        )
    ]


@register(Tags.models)
def check_role_field(app_configs, **kwargs):
    """
    Report a ``role`` field that cannot serve as the role claim.

    A user model without a ``role`` field is a supported configuration and says nothing
    here: the claim falls back to the staff flags. What is worth catching at startup is
    a field of that name meaning something else entirely, because the library will read
    it regardless and neither outcome announces itself:

        - A **relation** puts a model instance in the payload, and the token fails to
          encode. That is an error: every login and every rotation raises, so the
          installation does not work at all.
        - Anything **other than an integer** encodes fine and then quietly matches
          nothing. ``BasePermission`` compares the claim against
          :data:`~jwt_allauth.roles.STAFF_CODE` and
          :data:`~jwt_allauth.roles.SUPER_USER_CODE`, and ``'admin' != 1000``, so staff
          lose the access the class grants them by default. A project whose permission
          classes all declare ``accepted_roles`` of the same type is unaffected, which
          is why this is a warning and not an error.
    """
    from django.contrib.auth import get_user_model

    try:
        user_model = get_user_model()
    except Exception:  # pragma: no cover - a broken AUTH_USER_MODEL is Django's to report
        return []

    try:
        field = user_model._meta.get_field(ROLE_FIELD)
    except FieldDoesNotExist:
        # Roles are derived from the staff flags. A supported configuration.
        return []

    label = f"{user_model._meta.label}.{ROLE_FIELD}"

    if field.is_relation:
        return [
            Error(
                f"{label} is a relation, so it cannot be carried in the role claim.",
                hint=(
                    "The role claim has to be a JSON scalar. Point the field at the role "
                    "code itself, expose a `role` property returning it, or rename the "
                    "field so that jwt-allauth derives the role from is_staff/is_superuser."
                ),
                id=ROLE_FIELD_RELATION_ID,
                obj=user_model,
            )
        ]

    if not isinstance(field, models.IntegerField):
        return [
            Warning(
                f"{label} is not an integer field, so it will never match the built-in role codes.",
                hint=(
                    f"jwt_allauth.permissions.BasePermission grants staff and superusers "
                    f"access by comparing the role claim against STAFF_CODE ({STAFF_CODE}) and "
                    f"SUPER_USER_CODE ({SUPER_USER_CODE}). Store the role as an integer -- "
                    f"jwt_allauth.models.RoleMixin does -- or make sure every permission class "
                    f"declares accepted_roles of the type this field holds."
                ),
                id=ROLE_FIELD_TYPE_ID,
                obj=user_model,
            )
        ]

    return []


def _installed_major(distribution):
    """
    Major version of an installed distribution, or ``None`` when it cannot be read.

    Read from the installed metadata rather than from the package, so that it works the
    same for every upstream and does not depend on any of them exposing a version
    attribute. A version that does not start with a number is not worth guessing at:
    packaging allows a good deal more than ``major.minor``, and a wrong reading here
    would produce a warning about nothing.
    """
    try:
        raw = distribution_version(distribution)
    except PackageNotFoundError:
        return None
    head = raw.split('.', 1)[0]
    return int(head) if head.isdigit() else None


@register()
def check_upstream_versions(app_configs, **kwargs):
    """
    Report an upstream newer than any this release was tested against.

    The coupling to allauth and simplejwt runs through their internals rather than their
    documented surface: simplejwt's token and authentication classes are subclassed and
    its settings rewritten at startup, and allauth's TOTP and recovery-code helpers live
    under ``internal``. A new major of either can move that ground without anything
    failing at import, which is why a version number alone is worth reporting.

    Nothing here means the installation is broken. It means this combination is one
    nobody has run the suite against, and that its authentication is worth exercising
    before it reaches production.
    """
    messages = []
    for distribution, tested_major in sorted(TESTED_UPSTREAM_MAJORS.items()):
        major = _installed_major(distribution)
        if major is None or major <= tested_major:
            continue
        messages.append(
            Warning(
                f"{distribution} {major}.x is newer than the {tested_major}.x this "
                f"version of jwt-allauth was tested against.",
                hint=(
                    f"jwt-allauth builds on internals of {distribution}, so a new major "
                    f"can change behaviour it depends on without any error at import. "
                    f"Exercise login, refresh token rotation and MFA before deploying, "
                    f"and check for a newer jwt-allauth. This is a heads-up, not a fault: "
                    f"silence it with SILENCED_SYSTEM_CHECKS = ['{UNTESTED_UPSTREAM_ID}']."
                ),
                id=UNTESTED_UPSTREAM_ID,
            )
        )
    return messages
