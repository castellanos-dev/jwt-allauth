"""
Role codes, and where the role of an account comes from.

The role travels inside the token as the ``role`` claim, which is what lets the
permission classes authorize a request without touching the user table. Which number
lands in that claim depends on the user model of the installation:

    - A model that carries a ``role`` field decides its own roles, and the field is
      authoritative. :class:`~jwt_allauth.models.RoleMixin` adds that field to a user
      model, and :class:`~jwt_allauth.models.JAUser` is the mixin already applied.
    - A model without one falls back to the staff flags every Django user model has, so
      an installation that cannot swap ``AUTH_USER_MODEL`` -- which is most of them past
      their first migration -- still tells staff and superusers apart from regular
      users. What it cannot express is roles of its own, and adding ``RoleMixin`` to the
      model it already has is what unlocks those.

The fallback reproduces the constraints :class:`~jwt_allauth.models.JAUser` enforces, so
a project that adds the field later leaves the claims of the accounts that already
existed exactly where they were.
"""

from django.core.exceptions import FieldDoesNotExist

STAFF_CODE = 1000
SUPER_USER_CODE = 900
USER_CODE = 0

#: Attribute the role is read from, on both the user model and the token payload.
ROLE_FIELD = 'role'

# Tells "the attribute is not there" apart from "the attribute is there and holds
# None", which are answered differently below.
_MISSING = object()


def has_role_field(model) -> bool:
    """
    Whether a model stores a role of its own.

    Answers the *write* side of the question: a project can only be handed a role to
    assign -- through the admin-managed registration endpoint, through
    :class:`~jwt_allauth.models.UserManager` -- when there is a column to keep it in. A
    ``role`` exposed as a property is readable but not assignable, and is deliberately
    not counted here.

    Args:
        model: Model class to inspect.

    Returns:
        bool: True when the model declares a concrete ``role`` field.
    """
    try:
        model._meta.get_field(ROLE_FIELD)
    except (FieldDoesNotExist, AttributeError):
        return False
    return True


def user_model_has_role_field() -> bool:
    """
    Whether the user model of the installation stores a role of its own.

    Resolved at call time rather than at import: ``AUTH_USER_MODEL`` is not readable
    while the application registry is still loading, and tests swap it.

    Returns:
        bool: True when ``AUTH_USER_MODEL`` declares a concrete ``role`` field.
    """
    from django.contrib.auth import get_user_model

    return has_role_field(get_user_model())


def role_from_staff_flags(user) -> int:
    """
    Derive a role code from the staff flags of an account.

    The mapping is the one :class:`~jwt_allauth.models.JAUser` enforces with check
    constraints, so both paths agree on what a staff member and a superuser are:

        - ``is_staff`` -- :data:`STAFF_CODE`, whether or not the account is also a
          superuser. Staff is the wider of the two in this library: it is the flag the
          Django admin gates on.
        - ``is_superuser`` without ``is_staff`` -- :data:`SUPER_USER_CODE`.
        - anything else -- :data:`USER_CODE`.

    Args:
        user: Account to inspect.

    Returns:
        int: One of the role codes of this module.
    """
    if getattr(user, 'is_staff', False):
        return STAFF_CODE
    if getattr(user, 'is_superuser', False):
        return SUPER_USER_CODE
    return USER_CODE


def get_user_role(user):
    """
    Role of an account, as it goes into the ``role`` claim.

    Reads the ``role`` attribute when the user model has one -- a field, or a property
    computing it from something else -- and falls back to the staff flags when it has
    none. A nullable field left empty falls back too: a role of ``None`` would sit in
    the claim matching nothing, where :data:`USER_CODE` is what an account without a
    role of its own actually is.

    Args:
        user: Account whose role is being resolved.

    Returns:
        The stored role, or a code derived from the staff flags.
    """
    role = getattr(user, ROLE_FIELD, _MISSING)
    if role is _MISSING or role is None:
        return role_from_staff_flags(user)
    return role
