"""
Startup checks for configurations that would otherwise only fail in production.

Registered from :meth:`jwt_allauth.apps.JWTAllauthAppConfig.ready`, and run by
``manage.py check``, ``runserver`` and the deployment checks.
"""

from django.conf import settings
from django.core.checks import Tags, Warning, register
from django.urls import NoReverseMatch, reverse

from jwt_allauth.constants import EMAIL_VERIFIED_REDIRECT

#: Identifier of the check reported when the confirmation flow has nowhere to land.
VERIFIED_REDIRECT_ID = 'jwt_allauth.W001'


def _reverses(name, **kwargs):
    try:
        reverse(name, kwargs=kwargs)
    except NoReverseMatch:
        return False
    return True


@register(Tags.urls)
def check_verified_redirect(app_configs, **kwargs):
    """
    Report a confirmation flow that is routed but has no page to land on.

    ``EMAIL_VERIFIED_REDIRECT`` is where the browser goes once an address is confirmed;
    with it unset the flow falls back to the built-in page, which is only routed by the
    URLconf of ``jwt_allauth.registration``. A project that wires its endpoints by hand
    can therefore route the confirmation link without routing its destination, and that
    only shows up when an end user opens the link. The page is rendered in place when it
    happens, so this is a warning rather than an error, but the landing page is the
    project's to choose.
    """
    if not _reverses('account_confirm_email', key='key'):
        # The confirmation link is not routed at all: nothing to land on either.
        return []
    if getattr(settings, EMAIL_VERIFIED_REDIRECT, None):
        return []
    if _reverses('jwt_allauth_email_verified'):
        return []
    return [
        Warning(
            'The e-mail confirmation link is routed, but there is nowhere for it to land.',
            hint=(
                f"Set {EMAIL_VERIFIED_REDIRECT} to the page the browser should land on once an "
                f"address is confirmed, or route 'jwt_allauth_email_verified' by including "
                f"jwt_allauth.registration.urls. Until then the confirmation renders the "
                f"built-in page in place."
            ),
            id=VERIFIED_REDIRECT_ID,
        )
    ]
