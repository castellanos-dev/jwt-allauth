from django.test import SimpleTestCase, override_settings

from jwt_allauth.checks import VERIFIED_REDIRECT_ID, check_verified_redirect


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
