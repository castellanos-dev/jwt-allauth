"""
CSRF protection for the flows authenticated by a capability cookie.

The password reset and the admin-managed registration flows hand the browser a
one-time capability in a cookie, and the endpoint that consumes it authenticates from
that cookie alone. Django's CSRF check does not run for those endpoints: DRF exempts
its views from ``CsrfViewMiddleware`` and reinstates the check only inside
``SessionAuthentication``, which these endpoints do not use — they authenticate
through a permission class.

What stops another site from posting a new password to them is therefore only the
``SameSite='Lax'`` default of the capability cookie. That default is a deployment
setting: a frontend served from another origin needs ``SameSite='None'`` for the
cookie to travel at all, and once it is relaxed nothing is left. The check is run
explicitly wherever a capability cookie is accepted.

Set ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF = False`` to opt out, e.g. while migrating a
frontend that does not send the token yet. The built-in password forms send it
already.
"""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware, get_token
from rest_framework.exceptions import PermissionDenied

#: Name of the setting that governs the check.
CAPABILITY_CSRF_SETTING = 'JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF'


class _CSRFCheck(CsrfViewMiddleware):
    """``CsrfViewMiddleware`` that reports the rejection instead of rendering it."""

    def _reject(self, request, reason):
        # Returning the reason lets the caller answer with a DRF exception, rendered in
        # the format the client asked for, instead of the HTML failure view.
        return reason


def csrf_enforced() -> bool:
    """
    Whether requests authenticated by a capability cookie must carry a CSRF token.

    Read at call time so that ``override_settings`` and runtime changes are honoured.
    """
    return bool(getattr(settings, CAPABILITY_CSRF_SETTING, True))


def enforce_csrf(request) -> None:
    """
    Run Django's CSRF check on a request authenticated by a capability cookie.

    Args:
        request (Request): Request being served.

    Raises:
        PermissionDenied: if the request carries no valid CSRF token.
    """
    if not csrf_enforced():
        return

    check = _CSRFCheck(lambda _request: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied(f'CSRF Failed: {reason}')


def ensure_csrf_cookie(request) -> None:
    """
    Make the response to ``request`` carry a CSRF cookie.

    Called on the redirects that hand out a capability cookie, so that the frontend the
    link lands on can read the token and send it back when it posts the new password.

    Args:
        request (HttpRequest): Request whose response must carry the cookie.
    """
    if not csrf_enforced():
        return
    get_token(request)
