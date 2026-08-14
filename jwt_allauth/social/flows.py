"""
From a credential handed over by a provider to a user this library will mint a session for.

Two things shape this module.

The first is that it does not call ``allauth.socialaccount.helpers.complete_social_login()``.
That function opens a Django session and answers with redirects or by raising
``ImmediateHttpResponse``, which is the interactive flow; an API has to decide the same
questions and answer with JSON. The steps are therefore taken one at a time here, each
through allauth's public surface, so that every decision is visible at this level rather
than buried in a redirect chain.

The second is that the linking of a provider to an account that already exists is
governed here rather than by allauth. allauth links by e-mail through
``SOCIALACCOUNT_EMAIL_AUTHENTICATION``, and its ``SocialLogin._accept_login`` wipes the
local password every time it does. That is the right call when the local account may be
somebody else's, and the wrong one for the case this library cares about most -- an
account whose address was confirmed long ago, whose owner now wants to add Google and
keep signing in with their password too. So the verdict comes from
:func:`jwt_allauth.accounts.superseded_accounts`, the same rule registration uses, and
the two outcomes are told apart:

    * The address is **claimed** -- confirmed, or belonging to an account that has been
      used. Its owner is established, the provider has just proved control of the same
      mailbox, and the two are the same person. The provider is connected and nothing
      else about the account is touched.
    * The address is **unclaimed** -- never confirmed, on an account that was never
      used. Anybody could have typed it in. Those accounts are superseded exactly as
      registration supersedes them, and the provider account is created fresh.

All allauth imports are made inside the functions: ``allauth.socialaccount`` pulls in
``requests`` and ``pyjwt[crypto]`` through allauth's own extra, and ``jwt_allauth`` has
to import without them.
"""

from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework_simplejwt.settings import api_settings

from jwt_allauth.accounts import superseded_accounts
from jwt_allauth.exceptions import (
    SocialAccountAlreadyConnected,
    SocialDisconnectNotAllowed,
    SocialEmailConflict,
    SocialEmailUnverified,
    SocialFlowNotSupported,
    SocialLoginRejected,
    SocialProviderNotConfigured,
    SocialSignupClosed,
    SocialSignupNotAllowed,
    SocialTokenInvalid,
)
from jwt_allauth.social.app_settings import callback_url_allowed, email_linking_enabled, require_verified_email
from jwt_allauth.utils import is_email_verified, verification_is_mandatory

PROCESS_LOGIN = 'login'
PROCESS_CONNECT = 'connect'


def get_provider(request, provider_id: str, client_id: Optional[str] = None):
    """
    Resolve ``provider_id`` to a configured provider.

    ``client_id`` narrows the lookup when an installation registers several apps for the
    same provider. A ``client_id`` that matches none of them is reported as a bad
    credential rather than as an unknown provider: the provider *is* configured, and
    answering ``404`` would say otherwise while also telling an attacker which client
    ids exist.

    Args:
        request (HttpRequest): Current request.
        provider_id (str): Provider id as it appears in the URL, e.g. ``'google'``.
        client_id (str, optional): Client the credential was issued for.

    Returns:
        allauth.socialaccount.providers.base.Provider: The configured provider.

    Raises:
        SocialProviderNotConfigured: The id is unknown or nothing is registered for it.
        SocialTokenInvalid: The provider exists but not for that ``client_id``.
    """
    from allauth.socialaccount.adapter import get_adapter as get_social_adapter
    from allauth.socialaccount.models import SocialApp

    lookup_errors = (
        SocialApp.DoesNotExist,
        SocialApp.MultipleObjectsReturned,
        ImproperlyConfigured,
        KeyError,
    )
    try:
        return get_social_adapter().get_provider(request, provider_id, client_id=client_id)
    except lookup_errors:
        if client_id is None:
            raise SocialProviderNotConfigured()

    try:
        get_social_adapter().get_provider(request, provider_id)
    except lookup_errors:
        raise SocialProviderNotConfigured()
    raise SocialTokenInvalid(
        _("The credential was not issued for this application."),
        code='client_id_mismatch',
    )


def sociallogin_from_token(request, provider, data: Dict[str, Any]):
    """
    Verify a credential minted by the provider for one of its own clients.

    This is the flow a native or mobile SDK produces: the app talks to the provider
    directly and hands the resulting ``id_token`` or ``access_token`` over.

    Args:
        request (HttpRequest): Current request.
        provider: Provider resolved by :func:`get_provider`.
        data (dict): Validated body -- ``id_token``, ``access_token``, ``client_id``.

    Returns:
        allauth.socialaccount.models.SocialLogin: Populated, not yet persisted.

    Raises:
        SocialFlowNotSupported: The provider cannot verify a token out of band.
        SocialTokenInvalid: The credential is missing, belongs to another OAuth client,
            or the provider rejected it.
    """
    if not getattr(provider, 'supports_token_authentication', False):
        raise SocialFlowNotSupported()

    token = {k: data[k] for k in ('id_token', 'access_token') if data.get(k)}
    if not token:
        raise SocialTokenInvalid(_("Either an id_token or an access_token is required."), code='token_required')

    if getattr(provider, 'uses_apps', True):
        # The caller has to name the client the credential was issued for, so that the
        # provider can check the credential against it -- Google's `verify_token`, for
        # one, validates the `aud` claim against `app.client_id`. Letting it through
        # unnamed would mean silently picking whichever app is configured and verifying
        # a credential against a client it was never issued for. The value is then
        # matched against the resolved app, so that the name and the app agree.
        client_id = data.get('client_id')
        app = getattr(provider, 'app', None)
        if not client_id or app is None or client_id != app.client_id:
            raise SocialTokenInvalid(
                _("The credential was not issued for this application."),
                code='client_id_mismatch',
            )
        token['client_id'] = client_id

    try:
        return provider.verify_token(request, token)
    except ValidationError as e:
        raise SocialTokenInvalid(e.messages[0] if e.messages else None)


def sociallogin_from_code(request, provider, data: Dict[str, Any]):
    """
    Exchange an authorization code for the provider's own tokens, then read the profile.

    This is the flow a browser client produces. The code is bound to the client by PKCE
    when the provider supports it, which is why ``code_verifier`` is passed straight
    through rather than being interpreted here.

    Args:
        request (HttpRequest): Current request.
        provider: Provider resolved by :func:`get_provider`.
        data (dict): Validated body -- ``code``, ``callback_url``, ``code_verifier``.

    Returns:
        allauth.socialaccount.models.SocialLogin: Populated, not yet persisted.

    Raises:
        SocialFlowNotSupported: The provider does not speak OAuth2, or the caller sent a
            ``callback_url`` outside ``JWT_ALLAUTH_SOCIAL_CALLBACK_URLS``.
        SocialTokenInvalid: The provider refused the exchange or could not be reached.
    """
    import requests
    from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error

    callback_url = data['callback_url']
    if not callback_url_allowed(callback_url):
        raise SocialFlowNotSupported(
            _("This callback_url is not allowed."),
            code='callback_url_not_allowed',
        )

    try:
        adapter = provider.get_oauth2_adapter(request)
    except (ImproperlyConfigured, AttributeError):
        raise SocialFlowNotSupported()

    app = provider.app
    client = OAuth2Client(
        request,
        app.client_id,
        app.secret,
        adapter.access_token_method,
        adapter.access_token_url,
        callback_url,
        headers=getattr(adapter, 'headers', None),
        basic_auth=getattr(adapter, 'basic_auth', False),
    )

    try:
        token_data = client.get_access_token(data['code'], pkce_code_verifier=data.get('code_verifier'))
        token = adapter.parse_token(token_data)
        token.app = app
        sociallogin = adapter.complete_login(request, app, token, response=token_data)
    except (OAuth2Error, ValidationError, requests.RequestException) as e:
        raise SocialTokenInvalid(str(e) or None)

    sociallogin.token = token
    return sociallogin


def _prepare(request, sociallogin, process: str) -> None:
    """
    Resolve the social login against what is already in the database, then let the
    project inspect it.

    ``lookup()`` runs first so that the adapter hook and any receiver of
    ``pre_social_login`` see the user it resolved to rather than a placeholder. A
    receiver that vetoes the login raises ``ImmediateHttpResponse`` carrying a redirect,
    which is meaningless over an API, so it is turned into a refusal.
    """
    from allauth.core.exceptions import ImmediateHttpResponse
    from allauth.socialaccount import signals
    from allauth.socialaccount.adapter import get_adapter as get_social_adapter
    from allauth.socialaccount.models import SocialLogin

    sociallogin.state['process'] = process
    sociallogin.lookup()
    try:
        get_social_adapter().pre_social_login(request, sociallogin)
        signals.pre_social_login.send(sender=SocialLogin, request=request, sociallogin=sociallogin)
    except ImmediateHttpResponse:
        raise SocialLoginRejected()


def _verified_emails(sociallogin):
    """Addresses the provider itself vouched for, in the order it supplied them."""
    return [e for e in (sociallogin.email_addresses or []) if e.verified]


def _link_to_existing_account(sociallogin, email: str):
    """
    The account ``email`` already belongs to, when the provider may be linked to it.

    Returns ``None`` when the address is free or only held by sign-ups nobody ever
    claimed -- those are superseded by the caller, exactly as registration supersedes
    them -- and the account itself when somebody has established ownership of it.
    """
    pending = superseded_accounts(email)
    if pending is not None:
        return None

    from allauth.account.models import EmailAddress

    address = EmailAddress.objects.filter(email__iexact=email).select_related('user').first()
    if address is not None:
        return address.user
    # An installation that predates allauth's EmailAddress rows, or one whose user model
    # was populated by hand, can hold the address on the user alone.
    return get_user_model().objects.filter(email__iexact=email).first()


@transaction.atomic
def authenticate_social_login(request, sociallogin):
    """
    Turn a verified social login into the user a session will be minted for.

    The account is found in one of three ways, in this order: the provider account is
    already connected; the provider vouched for an address that an established local
    account holds, in which case the provider is connected to it and its password is
    left alone; or nothing matches and an account is created.

    Whichever way it went, the login then passes the same gates as one made with a
    password -- the account has to be active, and under mandatory verification its
    address has to be confirmed -- so that the two endpoints cannot disagree about who
    is allowed in.

    Args:
        request (HttpRequest): Current request.
        sociallogin (SocialLogin): Built by one of the ``sociallogin_from_*`` functions.

    Returns:
        User: The account to open a session for.

    Raises:
        SocialEmailUnverified: The provider vouched for no address.
        SocialEmailConflict: The address is somebody's and linking is off for this provider.
        SocialSignupClosed: Registration is closed to this login.
        SocialSignupNotAllowed: ``SOCIALACCOUNT_AUTO_SIGNUP`` is off, and an API has no
            sign-up form to fall back to.
        NotVerifiedEmail: The account exists and its address is still unconfirmed while
            verification is mandatory.
        rest_framework.exceptions.AuthenticationFailed: The account is not active.
    """
    _prepare(request, sociallogin, PROCESS_LOGIN)

    if not sociallogin.is_existing:
        user = _signup_or_link(request, sociallogin)
    else:
        user = sociallogin.user

    if not api_settings.USER_AUTHENTICATION_RULE(user):
        raise exceptions.AuthenticationFailed(
            _("No active account found with the given credentials"),
            "no_active_account",
        )
    if verification_is_mandatory():
        is_email_verified(user, raise_exception=True)

    if api_settings.UPDATE_LAST_LOGIN:
        update_last_login(None, user)

    return user


def _existing_owner(sociallogin, verified):
    """
    The established account one of the provider's verified addresses belongs to.

    ``None`` when no address is held by anyone, or is held only by sign-ups nobody ever
    claimed -- those are the caller's to supersede.

    Raises:
        SocialEmailConflict: An address is somebody's but linking is off for this
            provider, so there is no way to reach that account from here.
    """
    linking = email_linking_enabled(sociallogin.account.provider)
    for address in verified:
        owner = _link_to_existing_account(sociallogin, address.email)
        if owner is None:
            continue
        if not linking:
            raise SocialEmailConflict()
        return owner
    return None


def _signup(request, sociallogin, verified):
    """Create the account behind a social login that matched nothing."""
    from allauth.socialaccount.adapter import get_adapter as get_social_adapter

    adapter = get_social_adapter()
    if not adapter.is_open_for_signup(request, sociallogin):
        raise SocialSignupClosed()
    if not adapter.is_auto_signup_allowed(request, sociallogin):
        # allauth would render a sign-up form here. There is no form over an API, so
        # switching auto sign-up off means social sign-ups are off.
        raise SocialSignupNotAllowed()

    for address in verified:
        # Unclaimed sign-ups holding the address, removed whole rather than only losing
        # the address -- the same thing `RegisterSerializer._claim_email` does, for the
        # same reason: an account without an address is worse than no account.
        for pending in (superseded_accounts(address.email) or []):
            pending.delete()

    return adapter.save_user(request, sociallogin)


def _signup_or_link(request, sociallogin):
    """Resolve a social login that matched no existing provider account."""
    verified = _verified_emails(sociallogin)
    if not verified and require_verified_email():
        raise SocialEmailUnverified()

    owner = _existing_owner(sociallogin, verified)
    if owner is not None:
        # The provider proved control of an address whose owner is already established.
        # Connecting is all that is needed: the local password stays usable, so both
        # ways in keep working.
        sociallogin.connect(request, owner)
        return owner

    return _signup(request, sociallogin, verified)


def connect_social_login(request, sociallogin, user):
    """
    Attach a provider account to the caller's own account.

    Not an authentication event: no session is minted, and none of the caller's existing
    sessions are disturbed. The provider's addresses are not added to the account either
    -- ``SocialLogin.save(connect=True)`` skips ``setup_user_email`` -- so a provider
    cannot graft an address onto an account that did not choose it.

    Args:
        request (HttpRequest): Current request.
        sociallogin (SocialLogin): Built by one of the ``sociallogin_from_*`` functions.
        user (User): The authenticated caller.

    Returns:
        allauth.socialaccount.models.SocialAccount: The connection, new or already there.

    Raises:
        SocialAccountAlreadyConnected: The provider account belongs to somebody else. It
            is never re-pointed: that would be a way to take an account over.
    """
    _prepare(request, sociallogin, PROCESS_CONNECT)

    if sociallogin.is_existing:
        if sociallogin.user.pk != user.pk:
            raise SocialAccountAlreadyConnected()
        return sociallogin.account

    sociallogin.connect(request, user)
    return sociallogin.account


def disconnect_social_account(request, account, accounts) -> None:
    """
    Remove a provider connection, unless it is the only way into the account.

    Args:
        request (HttpRequest): Current request.
        account (SocialAccount): Connection to remove.
        accounts (list): Every connection the account holds, ``account`` included.

    Raises:
        SocialDisconnectNotAllowed: The adapter refused, which by default means this is
            the last connection of an account that has no usable password.
    """
    from allauth.socialaccount import signals
    from allauth.socialaccount.adapter import get_adapter as get_social_adapter
    from allauth.socialaccount.models import SocialAccount

    try:
        get_social_adapter().validate_disconnect(account, accounts)
    except ValidationError as e:
        raise SocialDisconnectNotAllowed(e.messages[0] if e.messages else None)

    account.delete()
    signals.social_account_removed.send(sender=SocialAccount, request=request, socialaccount=account)
