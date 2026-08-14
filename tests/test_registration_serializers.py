"""
The registration serializer decisions that the endpoint tests do not reach.

Two of them are the security of the module and neither announces itself when it goes
wrong: which existing account a sign-up is allowed to delete, and whether a failure to
warn the owner of an address can be observed from the outside.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework import serializers

from allauth.account.models import EmailAddress

from jwt_allauth.registration.serializers import RegisterSerializer, UserRegisterSerializer

SERIALIZER_LOGGER = 'jwt_allauth.registration.serializers'


class AccountIsClaimedTests(TestCase):
    """
    Which accounts a sign-up may take over -- which is to say, delete.

    ``_superseded_accounts`` asks this, and ``_claim_email`` deletes the user rows it
    hands back. Every branch answering "not claimed" by mistake is a sign-up that removes
    somebody else's account, and only the last of them was being exercised.
    """

    @staticmethod
    def _user(username, **fields):
        return get_user_model().objects.create_user(
            username, email=f'{username}@example.com', **fields)

    def test_no_account_behind_the_address_counts_as_claimed(self):
        # Nothing to supersede is not the same as free to supersede.
        self.assertTrue(RegisterSerializer._account_is_claimed(None))

    def test_a_staff_account_is_never_superseded(self):
        # The guard that stops a sign-up on an administrator's address from deleting the
        # administrator, however unverified that address happens to be.
        self.assertTrue(RegisterSerializer._account_is_claimed(self._user('staffer', is_staff=True)))

    def test_a_superuser_account_is_never_superseded(self):
        self.assertTrue(RegisterSerializer._account_is_claimed(self._user('root', is_superuser=True)))

    def test_an_account_that_has_ever_logged_in_is_claimed(self):
        # A login is proof somebody holds the password, whatever the address says.
        user = self._user('returning')
        user.last_login = timezone.now()
        user.save()
        self.assertTrue(RegisterSerializer._account_is_claimed(user))

    def test_an_account_with_a_verified_address_is_claimed(self):
        user = self._user('confirmed')
        EmailAddress.objects.create(
            user=user, email=user.email, verified=True, primary=True)
        self.assertTrue(RegisterSerializer._account_is_claimed(user))

    def test_a_sign_up_that_was_never_confirmed_is_not_claimed(self):
        # The one case the address is up for grabs: no login, no verified address, no
        # elevated flags.
        user = self._user('pending')
        EmailAddress.objects.create(
            user=user, email=user.email, verified=False, primary=True)
        self.assertFalse(RegisterSerializer._account_is_claimed(user))


class AccountAlreadyExistsMailTests(SimpleTestCase):
    """
    A failure to warn the owner of an address must not be observable.

    The notice goes out on the path that answers a taken address as though the sign-up
    had succeeded. An exception escaping here would be answered as a 500, which tells the
    caller exactly what the 200 was refusing to.
    """

    def test_a_delivery_failure_is_swallowed_and_logged(self):
        with patch(f'{SERIALIZER_LOGGER}.get_adapter') as adapter:
            adapter.return_value.send_account_already_exists_mail.side_effect = OSError('smtp down')
            with self.assertLogs(SERIALIZER_LOGGER, level='ERROR') as logged:
                RegisterSerializer._send_account_already_exists_mail('taken@example.com')
        self.assertTrue(any('account already exists' in line.lower() for line in logged.output))

    def test_a_successful_delivery_asks_the_adapter_for_the_address(self):
        with patch(f'{SERIALIZER_LOGGER}.get_adapter') as adapter:
            RegisterSerializer._send_account_already_exists_mail('taken@example.com')
        adapter.return_value.send_account_already_exists_mail.assert_called_once_with(
            'taken@example.com')


class ClaimEmailRaceTests(TestCase):
    """
    The window between validating an address and claiming it.

    Validation is read-only, so another request can take the address in between. What
    happens then has to match what validation would have done, or the endpoint answers
    one way under load and another way at rest -- which is an oracle of its own.
    """

    @staticmethod
    def _serializer(cls=RegisterSerializer, **validated):
        serializer = cls(data={})
        serializer._validated_data = {'email': 'taken@example.com', **validated}
        return serializer

    def test_an_address_taken_in_the_meantime_is_hidden_when_enumeration_is_prevented(self):
        serializer = self._serializer()
        with patch.object(RegisterSerializer, '_superseded_accounts', return_value=None), \
                patch.object(RegisterSerializer, '_hide_conflict', return_value=True), \
                patch.object(RegisterSerializer, '_absorb_password_hashing_cost'), \
                patch.object(RegisterSerializer, '_send_account_already_exists_mail'):
            self.assertFalse(serializer._claim_email())
        self.assertTrue(serializer.account_already_exists)

    def test_an_address_taken_in_the_meantime_is_reported_when_it_need_not_be_hidden(self):
        # The admin-managed endpoint, where the caller is entitled to be told.
        serializer = self._serializer()
        with patch.object(RegisterSerializer, '_superseded_accounts', return_value=None), \
                patch.object(RegisterSerializer, '_hide_conflict', return_value=False):
            with self.assertRaises(serializers.ValidationError) as raised:
                serializer._claim_email()
        self.assertIn('email', raised.exception.detail)

    def test_a_free_address_is_claimed(self):
        serializer = self._serializer()
        with patch.object(RegisterSerializer, '_superseded_accounts', return_value=[]):
            self.assertTrue(serializer._claim_email())
        self.assertFalse(serializer.account_already_exists)


class HiddenConflictSaveTests(TestCase):
    """A hidden conflict creates no account, on either registration endpoint."""

    def test_the_open_endpoint_creates_nothing(self):
        serializer = RegisterSerializer(data={})
        with patch.object(RegisterSerializer, '_claim_email', return_value=False):
            self.assertIsNone(serializer.save(None))

    def test_the_admin_endpoint_creates_nothing(self):
        serializer = UserRegisterSerializer(data={})
        with patch.object(UserRegisterSerializer, '_claim_email', return_value=False):
            self.assertIsNone(serializer.save(None))


class PasswordHashingCostTests(SimpleTestCase):
    """
    The dummy hash that keeps a hidden conflict from being timed.

    Sign-up hashes a password; the response that pretends a taken address was accepted
    has to pay the same cost, or the clock answers what the body refuses to.
    """

    @staticmethod
    def _serializer(**validated):
        serializer = RegisterSerializer(data={})
        serializer._validated_data = {'email': 'taken@example.com', **validated}
        return serializer

    def test_a_submitted_password_is_hashed_and_thrown_away(self):
        with patch(f'{SERIALIZER_LOGGER}.get_user_model') as user_model:
            self._serializer(password1='Test-Passw0rd')._absorb_password_hashing_cost()
        user_model.return_value.return_value.set_password.assert_called_once_with('Test-Passw0rd')

    def test_no_password_is_nothing_to_absorb(self):
        # The admin-managed endpoint takes no password, so there is no cost to match and
        # nothing to hash -- it must not reach for one that is not there.
        with patch(f'{SERIALIZER_LOGGER}.get_user_model') as user_model:
            self._serializer()._absorb_password_hashing_cost()
        user_model.return_value.return_value.set_password.assert_not_called()


class FieldValidationTests(SimpleTestCase):
    """The per-field validators, which nothing was reaching on their rejecting side."""

    def test_a_username_is_handed_to_the_adapter_to_clean(self):
        with patch(f'{SERIALIZER_LOGGER}.get_adapter') as adapter:
            adapter.return_value.clean_username.return_value = 'cleaned'
            self.assertEqual(RegisterSerializer().validate_username('  raw  '), 'cleaned')
        adapter.return_value.clean_username.assert_called_once_with('  raw  ')

    def test_a_first_name_with_anything_but_letters_is_rejected(self):
        for value in ('Ada99', 'Ada!', '<script>'):
            with self.subTest(value=value):
                with self.assertRaises(serializers.ValidationError):
                    RegisterSerializer().validate_first_name(value)

    def test_a_last_name_with_anything_but_letters_is_rejected(self):
        for value in ('Lovelace1', 'Love-lace', 'O_Brien'):
            with self.subTest(value=value):
                with self.assertRaises(serializers.ValidationError):
                    RegisterSerializer().validate_last_name(value)

    def test_accented_and_spaced_names_are_accepted_and_normalised(self):
        # The rejecting branch is only correct if the accepting one still takes the names
        # people actually have.
        self.assertEqual(RegisterSerializer().validate_first_name('ada  lovelace'), 'Ada Lovelace')
        self.assertEqual(RegisterSerializer().validate_last_name('ñandú'), 'Ñandú')
