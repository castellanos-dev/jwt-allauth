from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.models import Token as DefaultTokenModel

from jwt_allauth.utils import import_callable

TokenModel = import_callable(
    getattr(settings, 'REST_AUTH_TOKEN_MODEL', DefaultTokenModel))


class BaseToken(models.Model):
    id = models.BigAutoField(primary_key=True)
    created = models.DateTimeField(_("created"), auto_now_add=True)
    ip = models.GenericIPAddressField(_("ip"), blank=True, null=True, max_length=39)
    is_mobile = models.BooleanField(_("is mobile"), null=True)
    is_tablet = models.BooleanField(_("is tablet"), null=True)
    is_pc = models.BooleanField(_("is pc"), null=True)
    is_bot = models.BooleanField(_("is bot"), null=True)
    browser = models.CharField(_("browser"), max_length=32, blank=True, null=True)
    browser_version = models.CharField(_("browser version"), max_length=32, blank=True, null=True)
    os = models.CharField(_("os"), max_length=32, blank=True, null=True)
    os_version = models.CharField(_("os version"), max_length=32, blank=True, null=True)
    device = models.CharField(_("device"), max_length=32, blank=True, null=True)
    device_brand = models.CharField(_("device brand"), max_length=32, blank=True, null=True)
    device_model = models.CharField(_("device model"), max_length=32, blank=True, null=True)

    class Meta:
        abstract = True
        verbose_name = _("refresh token")
        verbose_name_plural = _("refresh tokens")


class AbstractRefreshToken(BaseToken):
    jti = models.CharField(_("jti"), max_length=32, blank=False)
    enabled = models.BooleanField(_("enabled"), default=True)
    session = models.CharField(_("session"), max_length=32, blank=False)

    class Meta:
        abstract = True
        verbose_name = _("refresh token")
        verbose_name_plural = _("refresh tokens")


class RefreshTokenWhitelistModel(AbstractRefreshToken):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens_whitelist",
        verbose_name=_("user"),
    )


class GenericTokenModel(BaseToken):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generic_tokens",
        verbose_name=_("user"),
    )
    token = models.CharField(_("token"), max_length=255, blank=False)
    purpose = models.CharField(_("purpose"), max_length=32, blank=False)
