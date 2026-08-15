"""
The two questions :mod:`jwt_allauth.accounts` answers, and why they are two.

One predicate used to serve both callers, and the pair below is what pulls them apart.
The test that matters most is the last one: an account that has been used is off limits
to a registration *and* out of reach of a provider, and a single predicate cannot say
both.
"""

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from jwt_allauth.accounts import (
    account_is_claimed,
    mailbox_control_proven,
    resolve_email_for_provider,
)
from jwt_allauth.constants import INVITATION
from jwt_allauth.tokens.models import GenericTokenModel
from jwt_allauth.utils import hash_token


def _user(username, email=None, verified=None, used=False, **fields):
    user = get_user_model().objects.create_user(
        username, email=email or f'{username}@example.com', **fields)
    if used:
        user.last_login = timezone.now()
        user.save()
    if verified is not None:
        EmailAddress.objects.create(user=user, email=user.email, verified=verified, primary=True)
    return user


class MailboxControlProvenTests(TestCase):
    """What earns a provider the right to be signed into an account that already exists."""

    def test_a_confirmed_address_proves_it(self):
        self.assertTrue(mailbox_control_proven(_user('confirmed', verified=True)))

    def test_a_login_does_not_prove_it(self):
        """
        The heart of the fix. A password login says somebody knows a password; on an
        account a stranger created, that stranger chose it. And a sign-up under
        ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` stamps ``last_login`` by itself, so
        this branch is not an edge case -- it is every unconfirmed account.
        """
        self.assertFalse(mailbox_control_proven(_user('returning', verified=False, used=True)))

    def test_a_live_invitation_proves_it(self):
        # The administrator sent the link to this address, which is exactly what the
        # provider has just proved control of.
        invited = _user('invited', verified=False)
        invited.set_unusable_password()
        invited.save()
        GenericTokenModel.objects.create(user=invited, token=hash_token('key'), purpose=INVITATION)
        self.assertTrue(mailbox_control_proven(invited))

    def test_a_staff_account_is_never_handed_over_by_default_nor_destroyed(self):
        # Both predicates have to say yes: no was a superuser deleted by the first social
        # sign-up for its address.
        staffer = _user('staffer', verified=False, is_staff=True)
        self.assertTrue(mailbox_control_proven(staffer))
        self.assertTrue(account_is_claimed(staffer))

    def test_no_account_proves_nothing(self):
        self.assertFalse(mailbox_control_proven(None))


class AccountIsClaimedIsTheWiderOneTests(TestCase):
    """
    ``account_is_claimed`` must never be narrower than ``mailbox_control_proven``.

    If it were, an account a provider is refused would still be deletable by a sign-up
    for the same address -- the takeover swapped for a data loss.
    """

    def test_a_used_account_is_claimed_but_unproven(self):
        user = _user('returning', verified=False, used=True)
        self.assertTrue(account_is_claimed(user))
        self.assertFalse(mailbox_control_proven(user))

    def test_every_proof_of_control_also_counts_as_claimed(self):
        for label, user in (
            ('confirmed', _user('confirmed', verified=True)),
            ('staff', _user('staffer', verified=False, is_staff=True)),
        ):
            with self.subTest(label):
                self.assertTrue(mailbox_control_proven(user))
                self.assertTrue(account_is_claimed(user))


class ResolveEmailForProviderTests(TestCase):
    """The three outcomes, which is one more than the registration resolver has."""

    def test_a_confirmed_address_resolves_to_its_owner(self):
        user = _user('confirmed', email='shared@example.com', verified=True)
        self.assertEqual(resolve_email_for_provider('shared@example.com'), (user, [], []))

    def test_a_used_but_unconfirmed_account_is_occupied_and_neither_bucket_else(self):
        user = _user('returning', email='shared@example.com', verified=False, used=True)
        owner, occupied, abandoned = resolve_email_for_provider('shared@example.com')
        self.assertIsNone(owner)
        self.assertEqual(occupied, [user])
        self.assertEqual(abandoned, [])

    def test_an_abandoned_sign_up_is_free_to_supersede(self):
        user = _user('pending', email='shared@example.com', verified=False)
        owner, occupied, abandoned = resolve_email_for_provider('shared@example.com')
        self.assertIsNone(owner)
        self.assertEqual(occupied, [])
        self.assertEqual(abandoned, [user])

    def test_an_address_nobody_holds_resolves_to_nothing(self):
        self.assertEqual(resolve_email_for_provider('free@example.com'), (None, [], []))

    def test_the_address_is_matched_the_way_allauth_stores_it(self):
        user = _user('confirmed', email='shared@example.com', verified=True)
        self.assertEqual(resolve_email_for_provider('Shared@Example.com')[0], user)


class VerificationOffStillProtectsAccountsTests(TestCase):
    """
    ``ACCOUNT_EMAIL_VERIFICATION = 'none'`` is why the fix is two predicates and not a
    stricter one.

    With verification off no address is ever confirmed, so making the single predicate
    require confirmation would have left every account in the installation free for any
    stranger to destroy by re-registering its address.
    """

    @override_settings(ACCOUNT_EMAIL_VERIFICATION='none', EMAIL_VERIFICATION=False)
    def test_a_used_account_cannot_be_superseded_with_verification_off(self):
        user = _user('returning', email='shared@example.com', verified=False, used=True)
        self.assertTrue(account_is_claimed(user))
