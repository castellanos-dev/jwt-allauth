from unittest.mock import patch

from django.db import connection, transaction
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from jwt_allauth.constants import REFRESH_TOKEN_COOKIE
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.tokens import RefreshToken
from jwt_allauth.utils import user_sessions_lock

from .mixins import TestsMixin


class LoginSessionBookkeepingTests(TestsMixin):
    """
    A login whitelists the session it hands out, and nothing else.
    """

    def setUp(self):
        self.init()
        RefreshTokenWhitelistModel.objects.filter(user=self.USER).delete()

    def _sessions(self):
        return RefreshTokenWhitelistModel.objects.filter(user=self.USER)

    @override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False)
    def test_login_whitelists_exactly_the_token_it_returns(self):
        """
        A second token minted and thrown away would leave a session nobody holds a
        credential for: `/logout/` can only close a session against its refresh token.
        """
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)

        self.assertEqual(self._sessions().count(), 1)
        self.assertEqual(
            self._sessions().first().jti,
            RefreshToken(resp['refresh']).payload['jti'],
        )

    def test_login_with_cookie_whitelists_exactly_the_token_it_returns(self):
        """Same with the refresh token delivered as a cookie."""
        response = self.client.post(self.login_url, data=self.LOGIN_PAYLOAD, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._sessions().count(), 1)
        self.assertEqual(
            self._sessions().first().jti,
            RefreshToken(response.cookies[REFRESH_TOKEN_COOKIE].value).payload['jti'],
        )

    @override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False)
    def test_every_session_of_a_login_can_be_closed(self):
        """Logging out with the token that was returned leaves nothing behind."""
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)
        self.token = resp['access']

        self.post(self.logout_url, data={'refresh': resp['refresh']}, status_code=200)

        self.assertFalse(self._sessions().exists())

    def test_login_authenticates_once(self):
        """
        The parent serializer would authenticate a second time, hashing the password
        again on every login.
        """
        with patch('jwt_allauth.login.serializers.allauth_authenticate', return_value=self.USER) as authenticate:
            self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)

        self.assertEqual(authenticate.call_count, 1)


class UserSessionsLockTests(TestsMixin):
    """
    Every writer of the session set of a user takes the same lock first.
    """

    def setUp(self):
        self.init()

    def _assert_locked_user(self, lock, calls=1):
        """The lock was taken, once per writer, on the row of the user under test."""
        self.assertEqual(lock.call_count, calls)
        # The claim of a token carries the id as a string; the query coerces it.
        self.assertEqual(str(lock.call_args.args[0]), str(self.USER.pk))

    def test_lock_is_taken_inside_a_transaction(self):
        self.assertFalse(transaction.get_connection().in_atomic_block)
        with user_sessions_lock(self.USER.pk):
            self.assertTrue(transaction.get_connection().in_atomic_block)
        self.assertFalse(transaction.get_connection().in_atomic_block)

    def test_lock_reads_the_user_row_for_update(self):
        """
        The row of the user is what orders a rotation against a revocation: locking the
        whitelist rows cannot, since the rotation inserts one.
        """
        if not connection.features.has_select_for_update:
            self.skipTest('backend without SELECT ... FOR UPDATE')

        with CaptureQueriesContext(connection) as queries:
            with user_sessions_lock(self.USER.pk):
                pass

        locking = [q['sql'] for q in queries if 'FOR UPDATE' in q['sql'].upper()]
        self.assertEqual(len(locking), 1, queries.captured_queries)
        self.assertIn(self.USER._meta.db_table, locking[0])

    def test_lock_without_a_user_is_a_no_op(self):
        """A token with no user claim locks nothing instead of raising."""
        with user_sessions_lock(None):
            pass

    def test_refresh_takes_the_lock_before_rotating(self):
        """Rotation is a writer of the set: it deletes one row and inserts another."""
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)

        with patch('jwt_allauth.token_refresh.serializers.user_sessions_lock',
                   wraps=user_sessions_lock) as lock:
            self.post(self.refresh_url, data={}, status_code=200)

        self._assert_locked_user(lock)

    def test_logout_all_takes_the_lock_before_revoking(self):
        self.token = self.ACCESS

        with patch('jwt_allauth.logout.views.user_sessions_lock', wraps=user_sessions_lock) as lock:
            self.post(self.logout_all_url, status_code=200)

        self._assert_locked_user(lock)
        self.assertFalse(RefreshTokenWhitelistModel.objects.filter(user=self.USER).exists())

    @override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False)
    def test_logout_takes_the_lock_before_revoking(self):
        """
        The successor of a rotation carries the session of the token it replaced, so the
        deletion by session has to be ordered against it too.
        """
        self.token = self.ACCESS

        with patch('jwt_allauth.logout.serializers.user_sessions_lock', wraps=user_sessions_lock) as lock:
            self.post(self.logout_url, data={'refresh': str(self.TOKEN)}, status_code=200)

        self._assert_locked_user(lock)
        self.assertFalse(
            RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti']).exists()
        )

    def test_replay_revokes_the_session_under_the_lock(self):
        """The revocation that reuse detection triggers is a writer of the set as well."""
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        self.post(self.refresh_url, data={}, status_code=200)

        # Replaying the consumed token takes the whole session down.
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        with patch('jwt_allauth.token_refresh.serializers.user_sessions_lock',
                   wraps=user_sessions_lock) as lock:
            self.post(self.refresh_url, data={}, status_code=401)

        self._assert_locked_user(lock, calls=2)
        self.assertFalse(
            RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists()
        )
