from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.models import UserManager as DefaultUserManager
from django.db import models
from django.db.models import Q

from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE


class UserManager(DefaultUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", STAFF_CODE)
        if extra_fields.get("role") != STAFF_CODE:
            raise ValueError(f"Staff must have role={STAFF_CODE}.")
        return super().create_superuser(username, email=email, password=password, **extra_fields)

    def create_user(self, username, email=None, password=None, **extra_fields):
        if extra_fields.get('is_staff', False) is True:
            extra_fields.setdefault("role", STAFF_CODE)
        elif extra_fields.get('is_superuser', False) is True:
            extra_fields.setdefault("role", SUPER_USER_CODE)
        return super().create_user(username, email=email, password=password, **extra_fields)


class JAUser(AbstractUser):
    objects = UserManager()

    role = models.PositiveSmallIntegerField(null=False, default=0)
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
            models.CheckConstraint(
                check=~Q(is_staff=True) | Q(role=STAFF_CODE),
                name=f"staff_role_equal_to_{STAFF_CODE}"
            ),
            models.CheckConstraint(
                check=~(~Q(is_staff=True) & Q(is_superuser=True)) | Q(role=SUPER_USER_CODE),
                name=f"superuser_role_equal_to_{SUPER_USER_CODE}"
            ),
        ]
