from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class JAUser(AbstractUser):
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
