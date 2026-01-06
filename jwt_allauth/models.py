from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.models import UserManager as DefaultUserManager
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from allauth.account.adapter import get_adapter
import datetime
import secrets

from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE
from jwt_allauth import app_settings


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


class PhoneAddress(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name=_('user'), on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=32, unique=True, verbose_name=_('phone number'))
    verified = models.BooleanField(verbose_name=_('verified'), default=False)

    class Meta:
        verbose_name = _('phone address')
        verbose_name_plural = _('phone addresses')

    def __str__(self):
        return self.phone_number

    def send_confirmation(self, request=None):
        confirmation = PhoneConfirmation.create(self)
        confirmation.send(request)
        return confirmation


class PhoneConfirmation(models.Model):
    phone_address = models.ForeignKey(PhoneAddress, verbose_name=_('phone address'), on_delete=models.CASCADE)
    created = models.DateTimeField(verbose_name=_('created'), default=timezone.now)
    sent = models.DateTimeField(verbose_name=_('sent'), null=True)
    key = models.CharField(verbose_name=_('key'), max_length=6)

    class Meta:
        verbose_name = _('phone confirmation')
        verbose_name_plural = _('phone confirmations')

    def __str__(self):
        return "confirmation for %s" % self.phone_address

    @classmethod
    def create(cls, phone_address):
        key = cls.generate_key()
        return cls.objects.create(phone_address=phone_address, key=key)

    @classmethod
    def generate_key(cls):
        # Generate a 6 digit random number
        return "{:06d}".format(secrets.randbelow(1000000))

    def send(self, request=None, **kwargs):
        adapter = get_adapter()
        adapter.send_confirmation_sms(request, self)
        self.sent = timezone.now()
        self.save()

    def confirm(self, request):
        if not self.key_expired():
            if not self.phone_address.verified:
                self.phone_address.verified = True
                self.phone_address.save()
            self.__class__.objects.filter(phone_address=self.phone_address).delete()
            return self.phone_address
        return None

    def key_expired(self):
        expiration_seconds = int(app_settings.PHONE_CONFIRMATION_EXPIRE_SECONDS)
        return self.created + datetime.timedelta(seconds=expiration_seconds) <= timezone.now()
