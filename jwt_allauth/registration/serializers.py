import logging
import re

from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.admin import EmailAddress
from allauth.account.models import get_emailconfirmation_model
from allauth.account.utils import setup_user_email
from allauth.utils import get_username_max_length
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from jwt_allauth.accounts import account_is_claimed, superseded_accounts
from jwt_allauth.roles import has_role_field, user_model_has_role_field
from jwt_allauth.utils import enumeration_prevented, verification_enabled

logger = logging.getLogger(__name__)

EMAIL_TAKEN_ERROR = _("A user is already registered with this e-mail address.")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=get_username_max_length(),
        min_length=allauth_settings.USERNAME_MIN_LENGTH,
        required=False
    )
    email = serializers.EmailField(required=True, max_length=100)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=True, write_only=True, max_length=100)
    last_name = serializers.CharField(required=True, write_only=True, max_length=100)

    _has_phone_field = False

    # Whether a conflict on the e-mail address has to be hidden from the caller.
    # Only the open endpoint needs it: an administrator registering somebody else is
    # entitled to know that the address is already in use.
    prevent_enumeration = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set when the address is already in use and the conflict is being hidden.
        # No account is created in that case, see `save`.
        self.account_already_exists = False

    def validate_username(self, username):
        username = get_adapter().clean_username(username)
        return username

    def validate_email(self, email):
        adapter = get_adapter()
        email = adapter.clean_email(email)
        if allauth_settings.UNIQUE_EMAIL and self._superseded_accounts(email) is None:
            if self._hide_conflict():
                # Answering with an error would turn the endpoint into an oracle:
                # anybody could ask it which addresses are registered. The request is
                # answered as a successful sign-up instead and the owner of the
                # address is warned by e-mail (see `save`).
                self.account_already_exists = True
            else:
                raise serializers.ValidationError(EMAIL_TAKEN_ERROR)
        return email

    def _hide_conflict(self):
        """
        Whether a conflict on the e-mail address must be hidden from this caller.
        """
        return self.prevent_enumeration and enumeration_prevented()

    # Both live in `jwt_allauth.accounts` now, because social login has to reach the
    # same verdict about the same address. Kept as methods so that a subclass which
    # overrides either one still governs this serializer.
    _account_is_claimed = staticmethod(account_is_claimed)
    _superseded_accounts = staticmethod(superseded_accounts)

    def _claim_email(self):
        """
        Free the validated address for the account that is about to be created.

        Superseded sign-ups are removed as a whole -- the user row included -- rather
        than only losing their address, which used to leave accounts behind that no
        longer had one. Nothing is deleted before this point: validation stays
        read-only so that a request that never gets here (an invalid password, say)
        cannot destroy a registration in progress.

        Returns:
            bool: ``False`` when no account is to be created because the address is
            already in use and the conflict is being hidden from the caller.
        """
        email = self.validated_data['email']
        if not self.account_already_exists and allauth_settings.UNIQUE_EMAIL:
            superseded = self._superseded_accounts(email)
            if superseded is None:
                # Claimed between validation and now.
                if not self._hide_conflict():
                    raise serializers.ValidationError({'email': [EMAIL_TAKEN_ERROR]})
                self.account_already_exists = True
            else:
                for user in superseded:
                    user.delete()

        if self.account_already_exists:
            self._absorb_password_hashing_cost()
            self._send_account_already_exists_mail(email)
            return False
        return True

    def _absorb_password_hashing_cost(self):
        """
        Hash the submitted password even though no account is going to be created.

        Skipping it would answer through the clock what the response refuses to say:
        hashing is by far the most expensive step of a sign-up.
        """
        password = self.validated_data.get('password1')
        if password:
            get_user_model()().set_password(password)

    @staticmethod
    def _send_account_already_exists_mail(email):
        """
        Warn the owner of ``email`` that somebody tried to sign up with their address.

        Delivery failures are logged and swallowed on purpose: an error response here
        would answer the very question the caller must not be able to ask.

        Args:
            email (str): Address that is already in use.
        """
        try:
            get_adapter().send_account_already_exists_mail(email)
        except Exception:
            logger.exception("Could not send the 'account already exists' notice.")

    def validate_password1(self, password):
        return get_adapter().clean_password(password)

    def validate_first_name(self, first_name):
        pattern = r'^[A-Za-zÀ-ÖØ-öø-ÿ ]+$'
        if not re.match(pattern, first_name):
            raise serializers.ValidationError('Incorrect format')
        first_name = re.sub(' +', ' ', first_name)
        return " ".join([txt.capitalize() for txt in first_name.split(" ")])

    def validate_last_name(self, last_name):
        pattern = r'^[A-Za-zÀ-ÖØ-öø-ÿ ]+$'
        if not re.match(pattern, last_name):
            raise serializers.ValidationError('Incorrect format')
        last_name = re.sub(' +', ' ', last_name)
        return " ".join([txt.capitalize() for txt in last_name.split(" ")])

    def validate(self, data):
        # Only validate passwords if they exist (not required for admin-managed registration)
        if 'password1' in data and 'password2' in data:
            if not constant_time_compare(data['password1'], data['password2']):
                raise serializers.ValidationError(_("The two password fields didn't match."))
        return data

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
        }

    @transaction.atomic
    def save(self, request):
        """
        Create the account.

        Returns:
            User|None: The new user, or ``None`` when the address is already in use
            and the caller is not being told about it.
        """
        if not self._claim_email():
            return None
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self, commit=False)
        self.custom_signup(request, user)
        user.save()
        setup_user_email(request, user, [])
        if not verification_enabled():
            email = EmailAddress.objects.filter(user=user.id).first()
            if email is not None:
                adapter.confirm_email(request, email)
        return user


class UserRegisterSerializer(RegisterSerializer):
    """
    Registration serializer for admin-managed user creation.
    - Requires email, and a role when the user model stores one.
    - Does not accept passwords; user sets password after email verification.
    - first_name/last_name optional.
    """
    # Remove password fields
    password1 = None  # type: ignore
    password2 = None  # type: ignore

    # Override optionality of names
    first_name = serializers.CharField(required=False, write_only=True, max_length=100)
    last_name = serializers.CharField(required=False, write_only=True, max_length=100)

    # Require explicit role. Dropped in `__init__` on a user model with nowhere to store
    # one: a required field that cannot be honoured would make the endpoint unusable,
    # and an optional one accepted and discarded would be worse. The endpoint itself
    # still works -- it grants no role, because there are none to grant.
    role = serializers.IntegerField(required=True, write_only=True)

    # The endpoint is restricted to administrators, who are entitled to know that an
    # address is already in use: there is nobody to hide it from.
    prevent_enumeration = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not user_model_has_role_field():
            self.fields.pop('role', None)

    def _accepts_role(self) -> bool:
        return 'role' in self.fields

    def validate(self, data):
        if self._accepts_role() and 'role' not in data:
            raise serializers.ValidationError({"role": _("Role is required")})
        return super().validate(data)

    def get_cleaned_data(self):
        base = super().get_cleaned_data()
        if self._accepts_role():
            base.update({
                'role': self.validated_data.get('role'),
            })
        return base

    def custom_signup(self, request, user):
        """
        Apply role and ensure no password is set at creation time.
        """
        cleaned = getattr(self, 'cleaned_data', {}) or {}
        role = cleaned.get('role')
        if role is not None and has_role_field(type(user)):
            try:
                user.role = int(role)
            except (TypeError, ValueError):
                pass
        # Prevent login until password is set
        user.set_unusable_password()

    @transaction.atomic
    def save(self, request):
        """
        Override to ignore EMAIL_VERIFICATION auto-confirm logic and always keep email unverified
        until the set-password step in admin-managed registration.
        """
        if not self._claim_email():
            return None
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self, commit=False)
        self.custom_signup(request, user)
        user.save()
        setup_user_email(request, user, [])
        # Create an EmailConfirmation instance for the user's primary email
        email_address = EmailAddress.objects.get_primary(user)
        if email_address is not None:
            confirmation_model = get_emailconfirmation_model()
            emailconfirmation = confirmation_model.create(email_address)
            adapter.send_confirmation_mail(request, emailconfirmation, signup=True)
        return user
