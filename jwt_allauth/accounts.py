"""
Whether an e-mail address is really somebody's.

Registration and social login both have to answer it, and they must answer it the same
way. An address that appears in the database is not proof of anything on its own: a
sign-up that was never confirmed and never used can have been made by anyone, with
anyone's address. What settles it is whether somebody has demonstrated control -- by
confirming the address, or by having used the account.

The two callers do different things with the answer. Registration supersedes the
unclaimed accounts and creates its own (:meth:`~jwt_allauth.registration.serializers.
RegisterSerializer._claim_email`). Social login links the provider to the claimed
account instead, leaving its password alone, because there the identity provider has
just demonstrated control of the same address (:mod:`jwt_allauth.social.flows`).
"""

from datetime import timedelta

from allauth.account import app_settings as allauth_app_settings
from allauth.account.models import EmailAddress
from django.utils import timezone

from jwt_allauth.constants import INVITATION
from jwt_allauth.tokens.models import GenericTokenModel


def account_is_claimed(user, reserve_invitations=True) -> bool:
    """
    Whether somebody has already established ownership of ``user``.

    Args:
        user (AbstractBaseUser): Owner of the address under evaluation.
        reserve_invitations (bool): Whether a live invitation counts as ownership. It
            does for everybody except the endpoint that issues invitations, which is
            also the one that reissues them -- see :func:`resolve_email`.

    Returns:
        bool: ``True`` unless the account is a sign-up that was never confirmed.
    """
    if user is None:
        return True
    if user.is_staff or user.is_superuser:
        return True
    if user.last_login is not None:
        return True
    if EmailAddress.objects.filter(user=user, verified=True).exists():
        return True
    return reserve_invitations and _has_open_invitation(user)


def _has_open_invitation(user) -> bool:
    """
    Whether an administrator created this account and its invitation is still live.

    An invited account looks exactly like an abandoned sign-up -- no password, never
    used, address unconfirmed -- so without this it was free for anybody to supersede: a
    stranger posting the invitee's address to the public sign-up destroyed the account,
    the role granted with it, and the link, and nobody was told. Somebody *did* establish
    control here; it was the administrator, and the invitation is the record of it.

    Bounded by the life of the link on purpose. Once the invitation expires it stops
    reserving the address: a dead invitation should not keep an e-mail address hostage.

    Both callers read this, and they act on it differently because their situations
    differ. Registration is the one it defends: it must not supersede the account. Social
    login links to it instead, and signs the invitee in as the account the administrator
    prepared -- there the provider has just proved control of the very address the
    invitation was sent to, which is what the link was asking for. The one caller it does
    not apply to is the endpoint that issues invitations, which has to be able to reissue
    its own; see the ``reserve_invitations`` argument.
    """
    if user.has_usable_password():
        # Cheap first: an invited account has no password until it claims one, so this
        # spares the query on every other unclaimed account.
        return False
    cutoff = timezone.now() - timedelta(days=allauth_app_settings.EMAIL_CONFIRMATION_EXPIRE_DAYS)
    return GenericTokenModel.objects.filter(
        user=user, purpose=INVITATION, created__gte=cutoff
    ).exists()


def resolve_email(email, reserve_invitations=True):
    """
    Who holds ``email``, in one query.

    Both callers need the same two facts about an address -- whether somebody has
    established ownership of it, and which accounts may be superseded if nobody has --
    and both used to ask twice, then throw the rows away and ask again to find out who
    the owner was. Asking once also settles a question two lookups cannot agree on: with
    ``ACCOUNT_UNIQUE_EMAIL`` off, several accounts can hold one address, and a second
    unordered query may return a different row from the one that reached the verdict.

    Args:
        email (str): Address to resolve. Matched against the column as allauth stores
            it, which is lower case: ``EmailAddress.clean`` and ``add_email`` both fold
            it on the way in, and allauth's own reverse lookup reads it back the same
            way. Case-insensitive matching would be correct too, and it is what this
            used to do, but ``UPPER(email) = UPPER(%s)`` cannot use the index allauth
            ships on the column, so every call scanned a table that only grows -- on a
            login path, now that social login asks the same question.
        reserve_invitations (bool): Whether a live invitation counts as ownership. Only
            :class:`~jwt_allauth.registration.serializers.UserRegisterSerializer` passes
            ``False``: the invitation reserves the address against everybody except the
            administrator who created it, who has to be able to reissue a lost link.

    Returns:
        tuple: ``(owner, superseded)``. ``owner`` is the account that established
        ownership, or ``None`` when nobody has; ``superseded`` lists the unclaimed
        accounts holding the address, and is empty when ``owner`` is set or the address
        is free.
    """
    accounts = []
    for address in EmailAddress.objects.filter(email=email.lower()).select_related('user'):
        if address.verified or account_is_claimed(address.user, reserve_invitations):
            return address.user, []
        accounts.append(address.user)
    return None, accounts


def superseded_accounts(email, reserve_invitations=True):
    """
    Accounts a registration for ``email`` is allowed to take over.

    An address is only up for grabs while nobody has proven control over it: it
    must be unverified and belong to an account that was never used. Anything
    else -- a verified address, a secondary address of an established account --
    is off limits, no matter that it is still pending confirmation.

    Args:
        email (str): Normalized address requested by the caller.
        reserve_invitations (bool): See :func:`resolve_email`.

    Kept as the shape :class:`~jwt_allauth.registration.serializers.RegisterSerializer`
    exposes and a subclass may override. :func:`resolve_email` is the one that answers
    both halves at once.

    Returns:
        list|None: Pending accounts to supersede, empty when the address is
        free, or ``None`` when the address is taken.
    """
    owner, superseded = resolve_email(email, reserve_invitations)
    return None if owner is not None else superseded
