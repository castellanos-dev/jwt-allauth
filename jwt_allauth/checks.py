"""
Startup checks for configurations that would otherwise only fail in production.

Registered from :meth:`jwt_allauth.apps.JWTAllauthAppConfig.ready`, and run by
``manage.py check``, ``runserver`` and the deployment checks.
"""

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
