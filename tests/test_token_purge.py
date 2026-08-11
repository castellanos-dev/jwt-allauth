from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from jwt_allauth.constants import (
    EMAIL_CONFIRMATION,
    REFRESH_TOKEN_COOKIE,
    MFA_PURPOSE_LOGIN_ATTEMPT,
    MFA_PURPOSE_LOGIN_CHALLENGE,
    MFA_PURPOSE_SETUP_CHALLENGE,
    MFA_PURPOSE_SETUP_SECRET,
    MFA_TOKEN_MAX_AGE_SECONDS,
    PASS_RESET,
    PASS_RESET_ACCESS,
)
from jwt_allauth.mfa.storage import (
    create_login_challenge,
    create_setup_challenge,
    get_login_challenge_user,
)
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.tokens.purge import (
    purge,
    purge_sessions,
    retentions,
    session_retention,
    unknown_purposes,
)
from .mixins import TestsMixin


class TokenPurgeTests(TestsMixin):
    """
    Rows nobody consumes have to be dropped on a schedule.

    A stored token is deleted when it is used, but an unopened reset link, an invitation
    nobody accepts or an MFA challenge abandoned at the code prompt is never used at all.
    """

    def setUp(self):
        self.init()

    def _store(self, purpose, age=None, token='stored-token'):
        entry = GenericTokenModel.objects.create(user=self.USER, token=token, purpose=purpose)
        if age is not None:
            GenericTokenModel.objects.filter(pk=entry.pk).update(created=timezone.now() - age)
        return entry

    def _purposes(self):
        return sorted(GenericTokenModel.objects.values_list('purpose', flat=True))

    def test_expired_rows_are_removed(self):
        for purpose, retention in retentions().items():
            self._store(purpose, age=retention + timedelta(seconds=1))

        removed = purge()

        self.assertEqual(set(removed), set(retentions()))
        self.assertEqual(GenericTokenModel.objects.count(), 0)

    def test_live_rows_are_kept(self):
        for purpose, retention in retentions().items():
            self._store(purpose, age=retention - timedelta(seconds=1))

        self.assertEqual(purge(), {})
        self.assertEqual(GenericTokenModel.objects.count(), len(retentions()))

    def test_dry_run_counts_without_deleting(self):
        self._store(PASS_RESET, age=timedelta(days=30))

        removed = purge(dry_run=True)

        self.assertEqual(removed, {PASS_RESET: 1})
        self.assertEqual(GenericTokenModel.objects.count(), 1)

    def test_unknown_purposes_are_left_alone(self):
        self._store('APPLICATION_OWN_PURPOSE', age=timedelta(days=365))

        purge()

        self.assertEqual(self._purposes(), ['APPLICATION_OWN_PURPOSE'])
        self.assertEqual(unknown_purposes(), {'APPLICATION_OWN_PURPOSE': 1})

    @override_settings(JWT_ALLAUTH_TOKEN_RETENTION={'APPLICATION_OWN_PURPOSE': timedelta(hours=1)})
    def test_retention_can_be_declared_for_an_unknown_purpose(self):
        self._store('APPLICATION_OWN_PURPOSE', age=timedelta(hours=2), token='old')
        self._store('APPLICATION_OWN_PURPOSE', age=timedelta(minutes=30), token='recent')

        self.assertEqual(purge(), {'APPLICATION_OWN_PURPOSE': 1})
        self.assertEqual(list(GenericTokenModel.objects.values_list('token', flat=True)), ['recent'])
        self.assertEqual(unknown_purposes(), {})

    @override_settings(JWT_ALLAUTH_TOKEN_RETENTION={PASS_RESET_ACCESS: timedelta(days=7)})
    def test_built_in_retention_can_be_overridden(self):
        self._store(PASS_RESET_ACCESS, age=timedelta(days=1))

        self.assertEqual(purge(), {})
        self.assertEqual(GenericTokenModel.objects.count(), 1)

    def test_retentions_follow_the_flows_they_belong_to(self):
        """Each retention mirrors the expiry the flow reading the row enforces itself."""
        with override_settings(PASSWORD_RESET_TIMEOUT=99, ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=7):
            configured = retentions()

        self.assertEqual(configured[PASS_RESET], timedelta(seconds=99))
        self.assertEqual(configured[EMAIL_CONFIRMATION], timedelta(days=7))
        self.assertEqual(
            configured[MFA_PURPOSE_LOGIN_CHALLENGE], timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS)
        )
        # Failed attempts double as the per-user counter, so they outlive the lockout window.
        self.assertGreaterEqual(
            configured[MFA_PURPOSE_LOGIN_ATTEMPT], timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS)
        )

    def test_management_command(self):
        self._store(PASS_RESET, age=timedelta(days=30))
        self._store(EMAIL_CONFIRMATION, age=timedelta(minutes=5))
        self._store('APPLICATION_OWN_PURPOSE', age=timedelta(days=365))

        out = StringIO()
        call_command('jwt_allauth_purge_tokens', stdout=out)
        output = out.getvalue()

        self.assertIn('1 expired row(s) deleted.', output)
        self.assertIn('APPLICATION_OWN_PURPOSE (1)', output)
        self.assertEqual(self._purposes(), ['APPLICATION_OWN_PURPOSE', EMAIL_CONFIRMATION])

    def test_management_command_dry_run(self):
        self._store(PASS_RESET, age=timedelta(days=30))

        out = StringIO()
        call_command('jwt_allauth_purge_tokens', '--dry-run', stdout=out)

        self.assertIn('1 expired row(s) would be deleted.', out.getvalue())
        self.assertEqual(GenericTokenModel.objects.count(), 1)


class SessionPurgeTests(TestsMixin):
    """
    The whitelist keeps a row per live refresh token, and expired ones are never read.

    A session is removed from the whitelist when it is rotated, revoked or logged out.
    Nothing removes the one left behind on a device that simply stops coming back.
    """

    def setUp(self):
        self.init()
        # init() opens a session; these tests are about what is left of it.
        self.session = RefreshTokenWhitelistModel.objects.get(jti=self.TOKEN['jti'])

    def _age(self, age):
        RefreshTokenWhitelistModel.objects.filter(pk=self.session.pk).update(
            created=timezone.now() - age
        )

    def test_expired_session_is_removed(self):
        self._age(session_retention() + timedelta(seconds=1))

        self.assertEqual(purge_sessions(), 1)
        self.assertFalse(RefreshTokenWhitelistModel.objects.filter(pk=self.session.pk).exists())

    def test_live_session_is_kept(self):
        self._age(session_retention() - timedelta(seconds=1))

        self.assertEqual(purge_sessions(), 0)
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(pk=self.session.pk).exists())

    def test_refresh_still_works_after_a_purge(self):
        """Only what the refresh endpoint would reject anyway is removed."""
        purge_sessions()

        self.client.cookies.load({REFRESH_TOKEN_COOKIE: str(self.TOKEN)})
        resp = self.client.post(self.refresh_url, content_type='application/json')

        self.assertEqual(resp.status_code, 200)

    def test_dry_run_counts_without_deleting(self):
        self._age(session_retention() + timedelta(seconds=1))

        self.assertEqual(purge_sessions(dry_run=True), 1)
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(pk=self.session.pk).exists())

    def test_retention_follows_the_refresh_token_lifetime(self):
        with override_settings(SIMPLE_JWT={'REFRESH_TOKEN_LIFETIME': timedelta(days=2)}):
            self.assertEqual(session_retention(), timedelta(days=2))

    def test_retention_never_undercuts_the_access_token_lifetime(self):
        """The row is also what the optional access token session check reads."""
        with override_settings(
            SIMPLE_JWT={
                'REFRESH_TOKEN_LIFETIME': timedelta(minutes=5),
                'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
            }
        ):
            self.assertEqual(session_retention(), timedelta(minutes=30))

    def test_management_command_reports_sessions(self):
        self._age(session_retention() + timedelta(seconds=1))

        out = StringIO()
        call_command('jwt_allauth_purge_tokens', stdout=out)
        output = out.getvalue()

        self.assertIn('expired sessions: 1 deleted', output)
        self.assertIn('1 expired row(s) deleted.', output)
        self.assertEqual(RefreshTokenWhitelistModel.objects.count(), 0)


class MFAChallengeStorageTests(TestsMixin):
    """The MFA challenge table is bounded and never turns a lookup into a server error."""

    def setUp(self):
        self.init()

    def _age(self, purpose, age):
        GenericTokenModel.objects.filter(purpose=purpose).update(created=timezone.now() - age)

    def test_duplicate_login_challenge_does_not_raise(self):
        challenge_id = create_login_challenge(self.USER.id)
        # Nothing at the database level forbids a second row for the same challenge.
        GenericTokenModel.objects.create(
            user=self.USER, token=challenge_id, purpose=MFA_PURPOSE_LOGIN_CHALLENGE
        )

        self.assertEqual(get_login_challenge_user(challenge_id).pk, self.USER.pk)

    def test_expired_login_challenges_do_not_pile_up(self):
        create_login_challenge(self.USER.id)
        self._age(MFA_PURPOSE_LOGIN_CHALLENGE, timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS + 1))

        create_login_challenge(self.USER.id)

        self.assertEqual(
            GenericTokenModel.objects.filter(purpose=MFA_PURPOSE_LOGIN_CHALLENGE).count(), 1
        )

    def test_expired_setup_challenges_do_not_pile_up(self):
        create_setup_challenge(self.USER.id)
        self._age(MFA_PURPOSE_SETUP_CHALLENGE, timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS + 1))

        create_setup_challenge(self.USER.id)

        self.assertEqual(
            GenericTokenModel.objects.filter(purpose=MFA_PURPOSE_SETUP_CHALLENGE).count(), 1
        )

    def test_a_live_challenge_of_another_user_is_untouched(self):
        other = get_user_model().objects.create_user('other', email='other@world.com', password=self.PASS)
        other_challenge = create_login_challenge(other.id)
        self._age(MFA_PURPOSE_LOGIN_CHALLENGE, timedelta(seconds=MFA_TOKEN_MAX_AGE_SECONDS + 1))
        GenericTokenModel.objects.filter(token=other_challenge).update(created=timezone.now())

        create_login_challenge(self.USER.id)

        self.assertIsNotNone(get_login_challenge_user(other_challenge))


class GenericTokenIndexTests(TestsMixin):
    """The columns every lookup narrows by are indexed."""

    def setUp(self):
        self.init()

    def test_lookup_columns_are_indexed(self):
        indexed = {tuple(index.fields) for index in GenericTokenModel._meta.indexes}

        self.assertIn(('token', 'purpose'), indexed)
        self.assertIn(('user', 'purpose'), indexed)
        self.assertIn(('purpose', 'created'), indexed)

    def test_single_use_lookup_uses_an_index(self):
        GenericTokenModel.objects.create(
            user=self.USER, token='indexed-token', purpose=MFA_PURPOSE_SETUP_SECRET
        )
        query_set = GenericTokenModel.objects.filter(
            token='indexed-token', purpose=MFA_PURPOSE_SETUP_SECRET
        )

        plan = str(query_set.explain())

        self.assertNotIn('SCAN', plan.upper())
