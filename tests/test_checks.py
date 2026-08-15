from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from jwt_allauth.checks import (
    SOCIAL_EMAIL_AUTHENTICATION_ID,
    SOCIAL_NO_PROVIDERS_ID,
    TESTED_UPSTREAM_MAJORS,
    UNTESTED_UPSTREAM_ID,
    VERIFIED_REDIRECT_ID,
    check_social_email_authentication,
    check_social_providers,
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


class SocialProvidersCheckTests(SimpleTestCase):
    """Social endpoints that cannot serve a request, and the silence a project deserves."""

    def test_silent_when_a_provider_is_configured(self):
        # tests/settings.py configures the dummy providers from settings.
        self.assertEqual(check_social_providers(None), [])

    @override_settings(SOCIALACCOUNT_PROVIDERS={})
    def test_silent_when_the_project_never_asked_for_social_login(self):
        """
        `startproject` writes 'allauth.socialaccount' into every generated project, so
        the app alone is not a request for social login. Warning there sent every new
        project a message telling it to go configure Google.
        """
        without_provider_app = [app for app in settings.INSTALLED_APPS
                                if app != 'tests.socialprovider']
        with override_settings(INSTALLED_APPS=without_provider_app):
            self.assertEqual(check_social_providers(None), [])

    @override_settings(SOCIALACCOUNT_PROVIDERS={'google': {'SCOPE': ['email']}})
    def test_warns_when_a_provider_is_declared_without_credentials(self):
        warnings = check_social_providers(None)
        self.assertEqual([w.id for w in warnings], [SOCIAL_NO_PROVIDERS_ID])

    @override_settings(SOCIALACCOUNT_PROVIDERS={'google': {'SCOPE': ['email']}})
    def test_reports_the_missing_extra_when_a_provider_is_configured_without_it(self):
        with patch('jwt_allauth.checks.socialaccount_stack_available', lambda: False):
            warnings = check_social_providers(None)
        self.assertEqual([w.id for w in warnings], [SOCIAL_NO_PROVIDERS_ID])
        self.assertIn('django-jwt-allauth[social]', warnings[0].hint)

    def test_silent_when_the_app_is_not_installed_at_all(self):
        without_socialaccount = [app for app in settings.INSTALLED_APPS
                                 if app not in ('allauth.socialaccount', 'tests.socialprovider')]
        with override_settings(INSTALLED_APPS=without_socialaccount):
            self.assertEqual(check_social_providers(None), [])


class SocialEmailAuthenticationCheckTests(SimpleTestCase):
    """allauth's flag governs allauth's views, not these endpoints."""

    def test_silent_when_the_setting_is_absent(self):
        self.assertEqual(check_social_email_authentication(None), [])

    @override_settings(SOCIALACCOUNT_EMAIL_AUTHENTICATION=True)
    def test_warns_when_the_setting_is_declared(self):
        warnings = check_social_email_authentication(None)
        self.assertEqual([w.id for w in warnings], [SOCIAL_EMAIL_AUTHENTICATION_ID])
        self.assertIn('JWT_ALLAUTH_SOCIAL_EMAIL_LINKING', warnings[0].hint)

    @override_settings(SOCIALACCOUNT_EMAIL_AUTHENTICATION=False)
    def test_warns_even_when_it_is_declared_false(self):
        # Setting it to False also says the project believes it has a say here.
        self.assertEqual([w.id for w in check_social_email_authentication(None)], [SOCIAL_EMAIL_AUTHENTICATION_ID])

    @override_settings(SOCIALACCOUNT_PROVIDERS={'dummy': {'EMAIL_AUTHENTICATION': True}})
    def test_warns_on_the_per_provider_form_too(self):
        # allauth reads the flag from three places; reporting only the global one would
        # leave the other two silently overridden.
        self.assertEqual([w.id for w in check_social_email_authentication(None)], [SOCIAL_EMAIL_AUTHENTICATION_ID])

    @override_settings(ROOT_URLCONF='empty_urls', SOCIALACCOUNT_EMAIL_AUTHENTICATION=True)
    def test_silent_when_the_endpoints_are_not_routed(self):
        self.assertEqual(check_social_email_authentication(None), [])
