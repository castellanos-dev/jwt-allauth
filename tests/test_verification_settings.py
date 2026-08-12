"""
Reconciliation of ``EMAIL_VERIFICATION`` with allauth's ``ACCOUNT_EMAIL_VERIFICATION``.

The two used to govern different halves of the feature with nothing keeping them in
step: this library's setting routed the confirmation URL and decided whether an address
is confirmed at sign-up, allauth's decided whether the mail is sent. A disagreeing pair
produced a state nobody designed — most sharply ``True`` with ``'none'``, which routed
the URL, left addresses unconfirmed and never sent a link to confirm them with.

``EMAIL_VERIFICATION`` now names the method and is the authoritative one; the resolution
runs once in ``AppConfig.ready`` and both settings come out of it saying the same thing.
"""

import warnings

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from jwt_allauth.apps import JWTAllauthAppConfig
from jwt_allauth.utils import verification_enabled, verification_is_mandatory


class _Settings:
    """Stand-in for the settings module, holding only what the resolution reads."""

    def __init__(self, **values):
        for name, value in values.items():
            setattr(self, name, value)


def resolve(**values):
    """Resolve a settings pair, returning the method and the warnings it raised."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        method = JWTAllauthAppConfig._resolve_email_verification(_Settings(**values))
    return method, [str(w.message) for w in caught]


class VerificationMethodResolutionTests(SimpleTestCase):

    # -- The shapes that already existed ---------------------------------------------

    def test_absent_setting_means_no_verification(self):
        self.assertEqual(resolve(), ('none', []))

    def test_booleans_keep_their_meaning(self):
        self.assertEqual(resolve(EMAIL_VERIFICATION=True), ('mandatory', []))
        self.assertEqual(resolve(EMAIL_VERIFICATION=False), ('none', []))

    def test_allauth_setting_still_selects_the_method(self):
        """
        Declaring allauth's setting is how ``'optional'`` was reachable before
        ``EMAIL_VERIFICATION`` could name it. It keeps working, without a warning.
        """
        for declared in ('mandatory', 'optional'):
            with self.subTest(declared=declared):
                self.assertEqual(
                    resolve(EMAIL_VERIFICATION=True, ACCOUNT_EMAIL_VERIFICATION=declared),
                    (declared, []),
                )

    # -- The method by name ------------------------------------------------------------

    def test_the_method_can_be_named(self):
        for method in ('mandatory', 'optional', 'none'):
            with self.subTest(method=method):
                self.assertEqual(resolve(EMAIL_VERIFICATION=method), (method, []))

    def test_the_method_is_case_insensitive(self):
        self.assertEqual(resolve(EMAIL_VERIFICATION='Optional'), ('optional', []))

    def test_an_unknown_method_is_refused(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve(EMAIL_VERIFICATION='optionnal')
        with self.assertRaises(ImproperlyConfigured):
            resolve(EMAIL_VERIFICATION=True, ACCOUNT_EMAIL_VERIFICATION='sometimes')

    # -- The pairs that used to fall between the two settings ---------------------------

    def test_a_named_method_wins_over_allauths(self):
        method, caught = resolve(
            EMAIL_VERIFICATION='optional', ACCOUNT_EMAIL_VERIFICATION='mandatory')
        self.assertEqual(method, 'optional')
        self.assertEqual(len(caught), 1)
        self.assertIn("disagree", caught[0])

    def test_true_with_none_is_resolved_rather_than_left_half_applied(self):
        """
        The pair that could never work: no link is sent, so no address is ever confirmed.
        """
        method, caught = resolve(EMAIL_VERIFICATION=True, ACCOUNT_EMAIL_VERIFICATION='none')
        self.assertEqual(method, 'none')
        self.assertEqual(len(caught), 1)
        self.assertIn("never delivers a confirmation link", caught[0])

    def test_false_keeps_verification_off_and_says_so(self):
        """
        A deployment running with the boolean off is running without verification,
        whatever it declared next to it. Honouring the declaration would turn
        verification on underneath it, so it is reported instead.
        """
        for declared in ('mandatory', 'optional'):
            with self.subTest(declared=declared):
                method, caught = resolve(
                    EMAIL_VERIFICATION=False, ACCOUNT_EMAIL_VERIFICATION=declared)
                self.assertEqual(method, 'none')
                self.assertEqual(len(caught), 1)
                self.assertIn("is ignored while", caught[0])

    def test_agreeing_pairs_are_silent(self):
        self.assertEqual(
            resolve(EMAIL_VERIFICATION='optional', ACCOUNT_EMAIL_VERIFICATION='optional'),
            ('optional', []),
        )
        self.assertEqual(
            resolve(EMAIL_VERIFICATION=False, ACCOUNT_EMAIL_VERIFICATION='none'),
            ('none', []),
        )


class NamedMethodAtRuntimeTests(SimpleTestCase):
    """
    ``ready`` normalises the setting to a boolean at startup, so a string only reaches
    the predicates when it is set afterwards — ``override_settings``, in practice. It
    must not be read as ``bool('none')``.
    """

    @override_settings(EMAIL_VERIFICATION='none')
    def test_named_none_is_not_truthy(self):
        self.assertFalse(verification_enabled())
        self.assertFalse(verification_is_mandatory())

    @override_settings(EMAIL_VERIFICATION='optional')
    def test_named_optional_enables_without_blocking(self):
        self.assertTrue(verification_enabled())
        self.assertFalse(verification_is_mandatory())

    @override_settings(EMAIL_VERIFICATION='mandatory')
    def test_named_mandatory_blocks(self):
        self.assertTrue(verification_enabled())
        self.assertTrue(verification_is_mandatory())
