from unittest.mock import patch

from rest_framework.generics import GenericAPIView
from rest_framework.throttling import AnonRateThrottle, BaseThrottle, ScopedRateThrottle, UserRateThrottle

from jwt_allauth.login.views import LoginView
from jwt_allauth.mfa.views import MFAVerifyView
from jwt_allauth.password_change.views import PasswordChangeView
from jwt_allauth.password_reset.views import PasswordResetView, ResetPasswordView, SetPasswordView
from jwt_allauth.registration.views import RegisterView
from jwt_allauth.throttling import ExtraThrottlesMixin
from jwt_allauth.token_refresh.views import TokenRefreshView

from .mixins import TestsMixin


class BlockingThrottle(BaseThrottle):
    """Stands in for the project throttle that a view used to displace."""

    def allow_request(self, request, view):
        return False

    def wait(self):
        return None


class ExtraThrottlesTests(TestsMixin):
    """
    The throttles a view declares are added to ``DEFAULT_THROTTLE_CLASSES`` instead of
    replacing them.
    """

    def setUp(self):
        self.init()

    @staticmethod
    def _throttle_classes(view_class, defaults=None):
        """Instantiate the view as DRF does and report the throttles it ends up with."""
        # ``APIView.throttle_classes`` is bound to ``DEFAULT_THROTTLE_CLASSES`` when the
        # class is created, so a project default is simulated by setting the attribute
        # rather than by overriding the setting.
        with patch.object(view_class, 'throttle_classes', defaults if defaults is not None else []):
            return [type(throttle) for throttle in view_class().get_throttles()]

    def test_view_throttle_is_kept_without_project_defaults(self):
        """Nothing changes for a project that configured no defaults."""
        self.assertEqual(self._throttle_classes(RegisterView), [AnonRateThrottle])

    def test_project_default_is_not_displaced(self):
        """The scoped throttle of the project survives next to the one of the view."""
        classes = self._throttle_classes(RegisterView, [ScopedRateThrottle])
        self.assertEqual(classes, [ScopedRateThrottle, AnonRateThrottle])

    def test_shared_throttle_is_not_applied_twice(self):
        """Two instances of one throttle would consume its bucket twice."""
        classes = self._throttle_classes(RegisterView, [AnonRateThrottle, UserRateThrottle])
        self.assertEqual(classes, [AnonRateThrottle, UserRateThrottle])

    def test_extra_throttles_can_be_dropped(self):
        """A project keeps full control by emptying ``extra_throttle_classes``."""
        with patch.object(RegisterView, 'extra_throttle_classes', ()):
            classes = self._throttle_classes(RegisterView, [ScopedRateThrottle])
        self.assertEqual(classes, [ScopedRateThrottle])

    def test_every_throttled_view_composes(self):
        """The regression was on registration, but every endpoint declared its own."""
        expected = {
            RegisterView: [AnonRateThrottle],
            LoginView: [AnonRateThrottle],
            TokenRefreshView: [UserRateThrottle],
            PasswordChangeView: [UserRateThrottle],
            PasswordResetView: [AnonRateThrottle],
            ResetPasswordView: [UserRateThrottle],
            SetPasswordView: [UserRateThrottle],
            MFAVerifyView: [AnonRateThrottle],
        }
        for view_class, own in expected.items():
            with self.subTest(view=view_class.__name__):
                self.assertEqual(
                    self._throttle_classes(view_class, [ScopedRateThrottle]),
                    [ScopedRateThrottle] + own,
                )

    def test_project_default_throttles_the_registration_endpoint(self):
        """End to end: a default that refuses the request answers ``429``."""
        with patch.object(RegisterView, 'throttle_classes', [BlockingThrottle]):
            self.post(
                self.register_url,
                data={
                    'email': 'throttled@email.com',
                    'password1': self.PASS,
                    'password2': self.PASS,
                    'first_name': self.FIRST_NAME,
                    'last_name': self.LAST_NAME,
                },
                status_code=429,
            )


class ExtraThrottlesMixinTests(TestsMixin):
    """The mixin on its own, away from the views of the library."""

    def setUp(self):
        self.init()

    def test_order_follows_the_declaration(self):
        class View(ExtraThrottlesMixin, GenericAPIView):
            throttle_classes = [ScopedRateThrottle]
            extra_throttle_classes = (AnonRateThrottle, UserRateThrottle)

        self.assertEqual(
            [type(throttle) for throttle in View().get_throttles()],
            [ScopedRateThrottle, AnonRateThrottle, UserRateThrottle],
        )

    def test_no_extra_throttles_declared(self):
        class View(ExtraThrottlesMixin, GenericAPIView):
            throttle_classes = [ScopedRateThrottle]

        self.assertEqual(
            [type(throttle) for throttle in View().get_throttles()],
            [ScopedRateThrottle],
        )
