"""
Resolution of the role claim across the user models an installation may have.

The library used to read ``user.role`` outright, which made its own user model a
precondition rather than a convenience: a project past its first migration cannot swap
``AUTH_USER_MODEL``, so it could not adopt the library at all. These tests pin the three
shapes that now have to work -- the shipped model, a model that mixed the field in, and
a model with no role of its own -- and the startup checks that catch the fourth, where
``role`` is a field of the project's meaning something else.
"""

from django.core.checks import Error, Warning
from django.db import models
from django.test import SimpleTestCase, override_settings

from jwt_allauth.checks import ROLE_FIELD_RELATION_ID, ROLE_FIELD_TYPE_ID, check_role_field
from jwt_allauth.models import JAUser, RoleMixin
from jwt_allauth.registration.serializers import UserRegisterSerializer
from jwt_allauth.roles import (
    STAFF_CODE,
    SUPER_USER_CODE,
    USER_CODE,
    get_user_role,
    has_role_field,
    role_from_staff_flags,
    user_model_has_role_field,
)
from jwt_allauth.tokens.app_settings import RefreshToken


class RolelessUser(models.Model):
    """A user model that never heard of this library: staff flags and nothing else."""
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    class Meta:
        app_label = 'jwt_allauth'


class MixedInRoleUser(RoleMixin, models.Model):
    """An existing user model that adopted the role field through the mixin."""
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    class Meta:
        app_label = 'jwt_allauth'


class NullableRoleUser(models.Model):
    """A role field the project left nullable, and rows that never filled it in."""
    role = models.PositiveSmallIntegerField(null=True, default=None)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    class Meta:
        app_label = 'jwt_allauth'


class PropertyRoleUser(models.Model):
    """A role computed rather than stored: readable, but nothing to assign to."""
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    class Meta:
        app_label = 'jwt_allauth'

    @property
    def role(self):
        return 42


class CharRoleUser(models.Model):
    """A ``role`` that is the project's own, and not a number."""
    role = models.CharField(max_length=32, default='member')

    class Meta:
        app_label = 'jwt_allauth'


class RelationRoleUser(models.Model):
    """A ``role`` pointing at a table of roles, which no token can carry."""
    role = models.ForeignKey('jwt_allauth.RefreshTokenWhitelistModel', null=True, on_delete=models.CASCADE)

    class Meta:
        app_label = 'jwt_allauth'


class StaffFlagFallbackTests(SimpleTestCase):
    """A model with no role of its own still has to tell staff apart from everyone else."""

    def test_staff_reads_as_staff(self):
        self.assertEqual(get_user_role(RolelessUser(is_staff=True)), STAFF_CODE)

    def test_staff_wins_over_superuser(self):
        # The mapping JAUser enforces with a check constraint: is_staff decides, whether
        # or not the account is also a superuser.
        user = RolelessUser(is_staff=True, is_superuser=True)
        self.assertEqual(get_user_role(user), STAFF_CODE)

    def test_superuser_without_staff_reads_as_superuser(self):
        user = RolelessUser(is_staff=False, is_superuser=True)
        self.assertEqual(get_user_role(user), SUPER_USER_CODE)

    def test_plain_account_reads_as_a_regular_user(self):
        self.assertEqual(get_user_role(RolelessUser()), USER_CODE)

    def test_the_fallback_matches_what_the_shipped_model_stores(self):
        # Adding the field later must not move the accounts that already existed, so the
        # two paths are pinned against each other rather than against literals.
        for is_staff, is_superuser in ((True, True), (True, False), (False, True), (False, False)):
            with self.subTest(is_staff=is_staff, is_superuser=is_superuser):
                derived = role_from_staff_flags(RolelessUser(is_staff=is_staff, is_superuser=is_superuser))
                manager_default = USER_CODE
                if is_staff:
                    manager_default = STAFF_CODE
                elif is_superuser:
                    manager_default = SUPER_USER_CODE
                self.assertEqual(derived, manager_default)

    def test_an_object_without_the_flags_at_all_is_a_regular_user(self):
        self.assertEqual(get_user_role(object()), USER_CODE)


class StoredRoleTests(SimpleTestCase):
    """A model that stores a role is the authority on it."""

    def test_the_field_wins_over_the_flags(self):
        # 700 is a role of the project's own: nothing derived from the flags could
        # produce it, so reading it back proves the field was consulted.
        self.assertEqual(get_user_role(MixedInRoleUser(role=700, is_staff=False)), 700)

    def test_the_field_wins_even_when_it_disagrees_with_the_flags(self):
        self.assertEqual(get_user_role(MixedInRoleUser(role=USER_CODE, is_staff=True)), USER_CODE)

    def test_the_mixin_defaults_to_a_regular_user(self):
        self.assertEqual(get_user_role(MixedInRoleUser()), USER_CODE)

    def test_a_computed_role_is_read_like_a_stored_one(self):
        self.assertEqual(get_user_role(PropertyRoleUser(is_staff=True)), 42)

    def test_an_empty_nullable_role_falls_back_rather_than_claiming_none(self):
        # None in the claim would match no permission class at all, where the account is
        # really just a user without a role of its own.
        self.assertEqual(get_user_role(NullableRoleUser(role=None)), USER_CODE)
        self.assertEqual(get_user_role(NullableRoleUser(role=None, is_staff=True)), STAFF_CODE)


class HasRoleFieldTests(SimpleTestCase):
    """Whether a role can be *assigned* is a different question from whether it can be read."""

    def test_the_shipped_model_stores_a_role(self):
        self.assertTrue(has_role_field(JAUser))

    def test_the_mixin_stores_a_role(self):
        self.assertTrue(has_role_field(MixedInRoleUser))

    def test_a_model_without_the_field_does_not(self):
        self.assertFalse(has_role_field(RolelessUser))

    def test_a_computed_role_does_not_count_as_storage(self):
        # Readable through get_user_role, but there is nothing to write to.
        self.assertFalse(has_role_field(PropertyRoleUser))

    def test_the_installation_is_read_from_auth_user_model(self):
        self.assertTrue(user_model_has_role_field())
        with override_settings(AUTH_USER_MODEL='jwt_allauth.RolelessUser'):
            self.assertFalse(user_model_has_role_field())


class RoleClaimTests(SimpleTestCase):
    """What ends up in the token, which is the only thing the permission classes see."""

    def test_the_claim_carries_the_stored_role(self):
        token = RefreshToken()
        token.set_user_role(MixedInRoleUser(role=700))
        self.assertEqual(token.payload['role'], 700)

    def test_the_claim_carries_the_derived_role(self):
        token = RefreshToken()
        token.set_user_role(RolelessUser(is_staff=True))
        self.assertEqual(token.payload['role'], STAFF_CODE)

    def test_the_derived_claim_is_json_encodable(self):
        # The whole point of the fallback is that a role-less installation can still
        # mint tokens; a value the encoder chokes on would fail every login.
        token = RefreshToken()
        token.set_user_role(RolelessUser(is_superuser=True))
        self.assertIsInstance(token.payload['role'], int)


class AdminRegistrationRoleFieldTests(SimpleTestCase):
    """The endpoint that assigns roles has to degrade rather than break."""

    @staticmethod
    def _serializer(**validated):
        """
        A serializer past validation, without going through the database.

        ``is_valid()`` queries the addresses to reject one already in use, which has
        nothing to do with roles and would tie every case here to a database.
        """
        serializer = UserRegisterSerializer(data={})
        serializer._validated_data = {'email': 'someone@example.com', **validated}
        return serializer

    def test_role_is_required_when_the_model_stores_one(self):
        self.assertTrue(UserRegisterSerializer().fields['role'].required)

    @override_settings(AUTH_USER_MODEL='jwt_allauth.RolelessUser')
    def test_role_is_dropped_when_the_model_stores_none(self):
        self.assertNotIn('role', UserRegisterSerializer().fields)

    def test_a_stored_role_is_carried_into_the_signup(self):
        self.assertEqual(self._serializer(role=700).get_cleaned_data()['role'], 700)

    @override_settings(AUTH_USER_MODEL='jwt_allauth.RolelessUser')
    def test_a_dropped_role_is_not_carried_into_the_signup(self):
        # Posted anyway, by a client written against an installation that had roles.
        self.assertNotIn('role', self._serializer(role=700).get_cleaned_data())

    def test_a_role_is_not_assigned_to_a_user_that_cannot_hold_it(self):
        # The serializer of an installation that stores roles, handed a user model that
        # does not: the assignment would land on the instance and never reach a column.
        serializer = self._serializer(role=700)
        serializer.cleaned_data = serializer.get_cleaned_data()
        user = RolelessUser()
        user.set_unusable_password = lambda: None
        serializer.custom_signup(None, user)
        self.assertFalse(hasattr(user, 'role'))

    def test_a_role_is_assigned_to_a_user_that_can(self):
        serializer = self._serializer(role=700)
        serializer.cleaned_data = serializer.get_cleaned_data()
        user = MixedInRoleUser()
        user.set_unusable_password = lambda: None
        serializer.custom_signup(None, user)
        self.assertEqual(user.role, 700)


class RoleFieldCheckTests(SimpleTestCase):
    """A `role` field meaning something else is a startup question, not a 500 at login."""

    def test_silent_on_the_shipped_model(self):
        self.assertEqual(check_role_field(None), [])

    @override_settings(AUTH_USER_MODEL='jwt_allauth.MixedInRoleUser')
    def test_silent_on_a_model_that_mixed_the_field_in(self):
        self.assertEqual(check_role_field(None), [])

    @override_settings(AUTH_USER_MODEL='jwt_allauth.RolelessUser')
    def test_silent_on_a_model_with_no_role_at_all(self):
        # The supported fallback, not a misconfiguration.
        self.assertEqual(check_role_field(None), [])

    @override_settings(AUTH_USER_MODEL='jwt_allauth.CharRoleUser')
    def test_warns_on_a_role_that_cannot_match_the_built_in_codes(self):
        messages = check_role_field(None)
        self.assertEqual([m.id for m in messages], [ROLE_FIELD_TYPE_ID])
        self.assertIsInstance(messages[0], Warning)

    @override_settings(AUTH_USER_MODEL='jwt_allauth.RelationRoleUser')
    def test_errors_on_a_role_no_token_could_carry(self):
        messages = check_role_field(None)
        self.assertEqual([m.id for m in messages], [ROLE_FIELD_RELATION_ID])
        self.assertIsInstance(messages[0], Error)
