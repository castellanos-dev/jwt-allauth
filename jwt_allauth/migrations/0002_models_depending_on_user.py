from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("jwt_allauth", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GenericTokenModel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "ip",
                    models.GenericIPAddressField(
                        blank=True, max_length=39, null=True, verbose_name="ip"
                    ),
                ),
                ("is_mobile", models.BooleanField(null=True, verbose_name="is mobile")),
                ("is_tablet", models.BooleanField(null=True, verbose_name="is tablet")),
                ("is_pc", models.BooleanField(null=True, verbose_name="is pc")),
                ("is_bot", models.BooleanField(null=True, verbose_name="is bot")),
                (
                    "browser",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="browser"
                    ),
                ),
                (
                    "browser_version",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="browser version"
                    ),
                ),
                (
                    "os",
                    models.CharField(blank=True, max_length=32, null=True, verbose_name="os"),
                ),
                (
                    "os_version",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="os version"
                    ),
                ),
                (
                    "device",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="device"
                    ),
                ),
                (
                    "device_brand",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="device brand"
                    ),
                ),
                (
                    "device_model",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="device model"
                    ),
                ),
                (
                    "token",
                    models.CharField(blank=False, max_length=255, verbose_name="token"),
                ),
                (
                    "purpose",
                    models.CharField(blank=False, max_length=32, verbose_name="purpose"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="generic_tokens",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PhoneAddress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(max_length=32, unique=True, verbose_name="phone number"),
                ),
                (
                    "verified",
                    models.BooleanField(default=False, verbose_name="verified"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "phone address",
                "verbose_name_plural": "phone addresses",
            },
        ),
        migrations.CreateModel(
            name="RefreshTokenWhitelistModel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "created",
                    models.DateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "ip",
                    models.GenericIPAddressField(
                        blank=True, max_length=39, null=True, verbose_name="ip"
                    ),
                ),
                ("is_mobile", models.BooleanField(null=True, verbose_name="is mobile")),
                ("is_tablet", models.BooleanField(null=True, verbose_name="is tablet")),
                ("is_pc", models.BooleanField(null=True, verbose_name="is pc")),
                ("is_bot", models.BooleanField(null=True, verbose_name="is bot")),
                (
                    "browser",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="browser"
                    ),
                ),
                (
                    "browser_version",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="browser version"
                    ),
                ),
                (
                    "os",
                    models.CharField(blank=True, max_length=32, null=True, verbose_name="os"),
                ),
                (
                    "os_version",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="os version"
                    ),
                ),
                (
                    "device",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="device"
                    ),
                ),
                (
                    "device_brand",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="device brand"
                    ),
                ),
                (
                    "device_model",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="device model"
                    ),
                ),
                (
                    "jti",
                    models.CharField(blank=False, max_length=32, verbose_name="jti"),
                ),
                (
                    "enabled",
                    models.BooleanField(default=True, verbose_name="enabled"),
                ),
                (
                    "session",
                    models.CharField(blank=False, max_length=32, verbose_name="session"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refresh_tokens_whitelist",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="user",
                    ),
                ),
            ],
            options={
                "verbose_name": "refresh token",
                "verbose_name_plural": "refresh tokens",
            },
        ),
        migrations.CreateModel(
            name="PhoneConfirmation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(default=django.utils.timezone.now, verbose_name="created"),
                ),
                (
                    "sent",
                    models.DateTimeField(null=True, verbose_name="sent"),
                ),
                ("key", models.CharField(max_length=6, verbose_name="key")),
                (
                    "phone_address",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="jwt_allauth.phoneaddress",
                        verbose_name="phone address",
                    ),
                ),
            ],
            options={
                "verbose_name": "phone confirmation",
                "verbose_name_plural": "phone confirmations",
            },
        ),
    ]
