"""
Revocation applied whenever the credentials of an account change.

Setting a password -- through the reset flow, through the change endpoint or through the
invitation flow -- is the moment at which the account changes hands, and it is the only
one. Everything that was outstanding until then was outstanding for whoever held the
account before, so it all goes down together: every session, the pending capabilities,
and any address change that had been started but not confirmed.

This matters most under ``ACCOUNT_EMAIL_VERIFICATION = 'optional'``, where an account is
usable before its address is confirmed. Somebody can sign up with an address that is not
theirs and hold a session on it; the owner's way out is the password reset, and it only
works if it takes *everything* with it. Half a revocation would leave the intruder a
refresh token, a reset capability of their own, or a second address queued up to take
over the account later.
"""

from allauth.account.models import EmailAddress
from django.conf import settings

from jwt_allauth.constants import MFA_PURPOSE_LOGIN_ATTEMPT
from jwt_allauth.tokens.models import GenericTokenModel, RefreshTokenWhitelistModel
from jwt_allauth.utils import user_sessions_lock


def revoke_on_credential_change(user_id) -> None:
    """
    Invalidate everything a credential change has to invalidate.

    Drops, for the given account:

        - **Every session**, the one asking for the change included. The caller is left
          without a refresh token on purpose: an endpoint that changes a password hands
          out a new session of its own, which is not the same as letting the old one
          survive.
        - **Every pending capability**: password reset and password set cookies that
          were handed out but never redeemed, unused e-mail confirmation tokens, and
          MFA setup challenges and secrets. The failed-MFA counter is left alone -- it
          is a rate limit, not a credential, and clearing it would make a password
          change a way to shake off a lockout.
        - **Every address change in flight**: an unconfirmed address that is not the
          primary one is a takeover waiting to be confirmed, so it does not survive the
          handover. allauth's confirmation rows go with it. The primary address is kept
          however unconfirmed it is: it is the account's own address, and under
          mandatory verification the confirmation link for it has not been followed yet.

    Honours ``LOGOUT_ON_PASSWORD_CHANGE``: an installation that sets it to ``False`` has
    opted out of revoking on credential changes, and nothing is dropped.

    Runs under :func:`~jwt_allauth.utils.user_sessions_lock`, like every other writer of
    the session set of a user: without it a refresh committing after the deletion began
    would leave the session it renews open past the credential change, which is the one
    outcome this whole function exists to prevent.

    Args:
        user_id (int|str): Account whose credentials just changed.
    """
    if not getattr(settings, 'LOGOUT_ON_PASSWORD_CHANGE', True):
        return

    with user_sessions_lock(user_id):
        RefreshTokenWhitelistModel.objects.filter(user=user_id).delete()
        GenericTokenModel.objects.filter(user=user_id).exclude(purpose=MFA_PURPOSE_LOGIN_ATTEMPT).delete()
        EmailAddress.objects.filter(user=user_id, verified=False, primary=False).delete()
