import django
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.models import UserManager as DefaultUserManager
from django.db import models
from django.db.models import Q

from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE, USER_CODE, has_role_field

# Django 5.1 renamed ``CheckConstraint(check=...)`` to ``condition`` and 6.0 removed the
# old spelling outright. Supported Djangos span both sides of that, so the argument is
# named at import time rather than written down.
_CONSTRAINT_CONDITION = 'condition' if django.VERSION >= (5, 1) else 'check'


def _check_constraint(condition, name):
    return models.CheckConstraint(name=name, **{_CONSTRAINT_CONDITION: condition})


class UserManager(DefaultUserManager):
    """
    Keeps the role of an account in step with its staff flags at creation time.

    Applies the same mapping as :func:`~jwt_allauth.roles.role_from_staff_flags`, so an
    account created through ``createsuperuser`` carries the role its flags imply instead
    of the default one. On a model without a role field it does nothing: there is
    nothing to keep in step, and passing ``role`` on to Django would only raise.
    """

    def _stores_role(self) -> bool:
        return has_role_field(self.model)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if self._stores_role():
            extra_fields.setdefault("role", STAFF_CODE)
            if extra_fields.get("role") != STAFF_CODE:
                raise ValueError(f"Staff must have role={STAFF_CODE}.")
        return super().create_superuser(username, email=email, password=password, **extra_fields)

    def create_user(self, username, email=None, password=None, **extra_fields):
        if self._stores_role():
            if extra_fields.get('is_staff', False) is True:
                extra_fields.setdefault("role", STAFF_CODE)
            elif extra_fields.get('is_superuser', False) is True:
                extra_fields.setdefault("role", SUPER_USER_CODE)
        return super().create_user(username, email=email, password=password, **extra_fields)


class RoleMixin(models.Model):
    """
    The role field, on its own, for a user model that already exists.

    Swapping ``AUTH_USER_MODEL`` is only realistic before the first migration, so a
    project past that point cannot adopt :class:`JAUser` however much it wants the
    roles. Adding this mixin to the user model it already has is the way in: one field,
    one migration, and the ``role`` claim starts carrying the project's own codes
    instead of the ones derived from the staff flags.

    .. code-block:: python

        from django.contrib.auth.models import AbstractUser
        from jwt_allauth.models import RoleMixin

        class MyUser(RoleMixin, AbstractUser):
            pass

    Existing rows take :data:`~jwt_allauth.roles.USER_CODE`, which is the right answer
    for every account except the staff ones -- those were reading as
    :data:`~jwt_allauth.roles.STAFF_CODE` through the fallback and would silently drop
    to a regular user. Backfill them in the same migration that adds the field::

        from django.db import migrations
        from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE

        def backfill_roles(apps, schema_editor):
            user = apps.get_model('myapp', 'MyUser')
            user.objects.filter(is_staff=True).update(role=STAFF_CODE)
            user.objects.filter(is_staff=False, is_superuser=True).update(role=SUPER_USER_CODE)

    The check constraints :class:`JAUser` declares are deliberately not part of this
    mixin: adding one to a populated table fails outright while a single staff row still
    holds the default role, which would leave the migration unrunnable on precisely the
    projects this mixin exists for. Declare them alongside the backfill if the guarantee
    is wanted.
    """
    role = models.PositiveSmallIntegerField(null=False, default=USER_CODE)

    class Meta:
        abstract = True


class JAUser(RoleMixin, AbstractUser):
    objects = UserManager()

    groups = models.ManyToManyField(
        Group,
        related_name="custom_users",
        related_query_name="custom_user",
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_users",
        related_query_name="custom_user",
        blank=True,
    )

    class Meta:
        constraints = [
            _check_constraint(
                ~Q(is_staff=True) | Q(role=STAFF_CODE),
                name=f"staff_role_equal_to_{STAFF_CODE}"
            ),
            _check_constraint(
                ~(~Q(is_staff=True) & Q(is_superuser=True)) | Q(role=SUPER_USER_CODE),
                name=f"superuser_role_equal_to_{SUPER_USER_CODE}"
            ),
        ]
