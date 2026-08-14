"""
The test helpers this library ships, in ``jwt_allauth.test``.

These run inside the suites of the projects using the library rather than in this one,
which is why nothing here had been exercising them: the suite has its own base classes in
``tests/mixins.py`` and never imports the module it publishes. A break in ``JATestCase``
therefore surfaces as a downstream suite failing, against a version already released.
"""

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from jwt_allauth.test import JAClient, JATestCase, user_field


class UserFieldTests(SimpleTestCase):
    """
    ``user_field`` sets a field it can find and skips one it cannot.

    A local equivalent of a helper that used to be imported from allauth's ``internal``
    package. The skip is not defensive padding: the user model of a project need not have
    ``first_name`` at all, and these helpers run against whatever model it brought.
    """

    def test_a_field_is_set(self):
        user = get_user_model()(username='u')
        user_field(user, 'first_name', 'Ada')
        self.assertEqual(user.first_name, 'Ada')

    def test_a_value_longer_than_the_column_is_truncated(self):
        # Django would not complain until the INSERT, and the fixture would fail with a
        # database error rather than with anything pointing at the test data.
        user = get_user_model()(username='u')
        max_length = get_user_model()._meta.get_field('first_name').max_length
        user_field(user, 'first_name', 'a' * (max_length + 10))
        self.assertEqual(len(user.first_name), max_length)

    def test_a_field_the_model_does_not_have_is_skipped(self):
        user = get_user_model()(username='u')
        user_field(user, 'no_such_field', 'value')
        self.assertFalse(hasattr(user, 'no_such_field'))

    def test_an_attribute_that_is_not_a_field_is_set_untruncated(self):
        # No column, so no max_length to truncate against.
        user = get_user_model()(username='u')
        user.nickname = ''
        user_field(user, 'nickname', 'a' * 500)
        self.assertEqual(len(user.nickname), 500)


class JATestCaseSetUpTests(JATestCase):
    """
    ``JATestCase`` builds the two accounts and the two tokens it promises.

    Subclassing it is the test: ``setUp`` runs before each of these, so anything it fails
    to build fails here rather than in somebody else's suite.
    """

    def test_both_accounts_exist_with_their_names(self):
        self.assertEqual(self.USER.email, self.EMAIL)
        self.assertEqual(self.USER.first_name, self.FIRST_NAME)
        self.assertEqual(self.STAFF_USER.email, self.STAFF_EMAIL)
        self.assertEqual(self.STAFF_USER.first_name, self.STAFF_FIRST_NAME)

    def test_the_staff_account_is_staff(self):
        self.assertTrue(self.STAFF_USER.is_staff)
        self.assertFalse(self.USER.is_staff)

    def test_both_addresses_are_verified(self):
        # Unverified, every authenticated request in a downstream suite would answer 403
        # under mandatory verification.
        from allauth.account.models import EmailAddress

        for user in (self.USER, self.STAFF_USER):
            with self.subTest(user=user.email):
                self.assertTrue(
                    EmailAddress.objects.filter(user=user, verified=True, primary=True).exists()
                )

    def test_the_two_tokens_belong_to_the_two_accounts(self):
        # Compared as strings: Simple JWT writes the id claim as text, and this is not
        # the place to pin which.
        self.assertNotEqual(self.ACCESS, self.STAFF_ACCESS)
        self.assertEqual(str(self.TOKEN['user_id']), str(self.USER.pk))
        self.assertEqual(str(self.STAFF_TOKEN['user_id']), str(self.STAFF_USER.pk))

    def test_the_client_authenticates_as_the_regular_user(self):
        response = self.ja_client.auth_get('/jwt-allauth/user/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['email'], self.EMAIL)

    def test_the_client_authenticates_as_the_staff_user(self):
        response = self.ja_client.staff_get('/jwt-allauth/user/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['email'], self.STAFF_EMAIL)

    def test_an_unauthenticated_request_is_refused(self):
        # The bare verbs must not carry a token of their own, or every test written with
        # them would pass authorization it never asked for.
        self.assertEqual(self.ja_client.get('/jwt-allauth/user/').status_code, 401)

    def test_a_token_can_be_injected_directly(self):
        response = self.ja_client.get('/jwt-allauth/user/', access_token=self.STAFF_ACCESS)
        self.assertEqual(response.json()['email'], self.STAFF_EMAIL)

    #: Verbs that are supposed to carry a token, and the account each speaks for.
    AUTHENTICATED_VERBS = (
        'auth_post', 'auth_patch', 'auth_put', 'auth_delete',
        'staff_post', 'staff_patch', 'staff_put', 'staff_delete',
    )

    #: Verbs that are supposed to carry nothing unless handed a token.
    BARE_VERBS = ('post', 'patch', 'put', 'delete')

    def test_every_authenticated_verb_attaches_its_token(self):
        # ``/jwt-allauth/user/`` answers only GET and PATCH, so most of these come back
        # 405 -- which is the assertion. DRF authenticates before it resolves the
        # handler, so a 405 proves the request got through authentication, where a 401
        # would mean the verb forgot the header it exists to attach.
        for verb in self.AUTHENTICATED_VERBS:
            with self.subTest(verb=verb):
                response = getattr(self.ja_client, verb)('/jwt-allauth/user/')
                self.assertNotEqual(response.status_code, 401)

    def test_every_bare_verb_sends_no_token_of_its_own(self):
        # The mirror of the above: a bare verb that quietly authenticated would let a
        # downstream test pass authorization it never asked for.
        for verb in self.BARE_VERBS:
            with self.subTest(verb=verb):
                response = getattr(self.ja_client, verb)('/jwt-allauth/user/')
                self.assertEqual(response.status_code, 401)

    def test_authenticate_swaps_the_account_the_client_speaks_for(self):
        self.authenticate(self.STAFF_USER)
        self.assertEqual(
            JAClient(self.ACCESS, self.STAFF_ACCESS).auth_get('/jwt-allauth/user/').json()['email'],
            self.STAFF_EMAIL,
        )
