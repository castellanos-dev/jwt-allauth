from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from jwt_allauth.checks import (
    TESTED_UPSTREAM_MAJORS,
    UNTESTED_UPSTREAM_ID,
    VERIFIED_REDIRECT_ID,
    check_upstream_versions,
    check_verified_redirect,
)


class VerifiedRedirectCheckTests(SimpleTestCase):
    """The confirmation flow must have somewhere to land, and it is a startup question."""

    def test_no_warning_when_the_built_in_page_is_routed(self):
        self.assertEqual(check_verified_redirect(None), [])

    @override_settings(EMAIL_VERIFIED_REDIRECT='/verified/')
    def test_no_warning_when_a_redirect_is_configured(self):
        self.assertEqual(check_verified_redirect(None), [])

    @override_settings(ROOT_URLCONF='handwired_urls')
    def test_warns_when_the_confirmation_has_nowhere_to_land(self):
        warnings = check_verified_redirect(None)
        self.assertEqual([w.id for w in warnings], [VERIFIED_REDIRECT_ID])

    @override_settings(ROOT_URLCONF='handwired_urls', EMAIL_VERIFIED_REDIRECT='/verified/')
    def test_no_warning_when_the_hand_wired_project_configured_a_redirect(self):
        self.assertEqual(check_verified_redirect(None), [])

    @override_settings(ROOT_URLCONF='empty_urls')
    def test_no_warning_when_the_confirmation_is_not_routed_at_all(self):
        self.assertEqual(check_verified_redirect(None), [])


class UpstreamVersionCheckTests(SimpleTestCase):
    """
    What replaced the upper bounds on allauth and simplejwt.

    The caps blocked the install of any newer major, security releases included. The
    check lets it through and says so instead, so the warning has to fire exactly when
    the combination is one the suite has never run against — a false positive here is a
    warning every project sees forever.
    """

    @staticmethod
    def _with_versions(**versions):
        """Patch the installed version of each named distribution."""
        def fake_version(distribution):
            try:
                return versions[distribution]
            except KeyError:
                raise PackageNotFoundError(distribution)
        return patch('jwt_allauth.checks.distribution_version', fake_version)

    def test_silent_on_the_versions_actually_installed(self):
        # The suite runs against a supported combination, so the check has to be silent
        # here or it would be warning about itself.
        self.assertEqual(check_upstream_versions(None), [])

    def test_silent_on_the_tested_major(self):
        versions = {name: f'{major}.19.1' for name, major in TESTED_UPSTREAM_MAJORS.items()}
        with self._with_versions(**versions):
            self.assertEqual(check_upstream_versions(None), [])

    def test_warns_once_per_upstream_that_moved_ahead(self):
        versions = {name: f'{major + 1}.0.0' for name, major in TESTED_UPSTREAM_MAJORS.items()}
        with self._with_versions(**versions):
            messages = check_upstream_versions(None)
        self.assertEqual(len(messages), len(TESTED_UPSTREAM_MAJORS))
        self.assertEqual({m.id for m in messages}, {UNTESTED_UPSTREAM_ID})

    def test_names_the_upstream_that_moved(self):
        tested = TESTED_UPSTREAM_MAJORS['django-allauth']
        with self._with_versions(**{'django-allauth': f'{tested + 1}.0.0'}):
            messages = check_upstream_versions(None)
        self.assertEqual(len(messages), 1)
        self.assertIn('django-allauth', messages[0].msg)

    def test_silent_when_an_upstream_is_not_installed(self):
        # The MFA extra is optional, and a missing distribution is Django's to complain
        # about, not this check's.
        with self._with_versions():
            self.assertEqual(check_upstream_versions(None), [])

    def test_silent_on_a_version_that_does_not_start_with_a_number(self):
        # Packaging allows more than major.minor; guessing at it would warn about nothing.
        with self._with_versions(**{name: 'nightly' for name in TESTED_UPSTREAM_MAJORS}):
            self.assertEqual(check_upstream_versions(None), [])

    def test_silent_on_an_older_major(self):
        versions = {name: f'{major - 1}.0.0' for name, major in TESTED_UPSTREAM_MAJORS.items()}
        with self._with_versions(**versions):
            self.assertEqual(check_upstream_versions(None), [])
