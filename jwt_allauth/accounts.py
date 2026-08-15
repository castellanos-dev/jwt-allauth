"""
Whether an e-mail address is really somebody's.

Registration and social login both have to ask about an address, and they are **not**
asking the same thing -- which is the correction this module carries, because one
predicate used to answer both:

* Registration asks *may I destroy this account to make room for a new sign-up?*
  Anything short of an abandoned sign-up must answer yes-it-is-taken, ``last_login``
  included: somebody has been working in there, whoever they are.
  (:meth:`~jwt_allauth.registration.serializers.RegisterSerializer._claim_email`.)
* Social login asks *may I hand this account to whoever a provider vouches for?* Only
  proof of control of the mailbox justifies that, and ``last_login`` is not such proof
  -- see :func:`mailbox_control_proven`. (:mod:`jwt_allauth.social.flows`.)

Answering the second question with the first one was an account-takeover: under
``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` a sign-up stamps its own ``last_login``, so
every address anybody had ever typed into the form counted as proven, and the provider
handed the owner's session to whoever had typed it first.

Hence the two predicates below. :func:`account_is_claimed` is the weaker one and is
literally the stronger one plus ``last_login``, so the two cannot drift apart: a fact
added to :func:`mailbox_control_proven` reaches both.
"""

from datetime import timedelta

from allauth.account import app_settings as allauth_app_settings
from allauth.account.models import EmailAddress
from django.utils import timezone

from jwt_allauth.constants import INVITATION
from jwt_allauth.tokens.models import GenericTokenModel


def mailbox_control_proven(user, reserve_invitations=True) -> bool:
    """
    Whether somebody has demonstrated control of the **address itself**.

    The question social login has to ask, and the only one that justifies handing an
    account that already exists to whoever an identity provider vouches for.

    ``last_login`` is deliberately absent, and no amount of fixing *when* it is stamped
    would earn it a place here. Signing up stamps it -- ``complete_signup`` logs the new
    account in under ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` -- and even a genuine
    password login proves only that somebody knows a password, which for an account
    created by a stranger is a password that stranger chose. Neither says anything about
    the mailbox. What does: the address was confirmed, an administrator provisioned the
    account for that address, or the account is a privileged one nobody self-serviced
    into existence.

    Args:
        user (AbstractBaseUser): Owner of the address under evaluation.
        reserve_invitations (bool): Whether a live invitation counts as proof. It does
            for everybody except the endpoint that issues invitations, which is also the
            one that reissues them -- see :func:`resolve_email`.

    Returns:
        bool: ``True`` when control of the address has been demonstrated.
    """
    if user is None:
        # Fail closed in the direction that matters here: nothing is handed over.
        return False
    if user.is_staff or user.is_superuser:
        # Not something anybody talked their way into: an operator created it with this
        # address on purpose, which is a record of control in the same way an invitation
        # is. It also has to be here rather than only in `account_is_claimed`, or a
        # freshly provisioned superuser would read as an abandoned sign-up and be
        # superseded by the first social sign-up for its address.
        return True
    if EmailAddress.objects.filter(user=user, verified=True).exists():
        return True
    # An open invitation stays on purpose: the administrator sent the link to THIS
    # address, and the provider has just proved control of it, which is precisely what
    # the invitation was asking for.
    return reserve_invitations and _has_open_invitation(user)


def account_is_claimed(user, reserve_invitations=True) -> bool:
    """
    Whether the account is in use and must not be destroyed.

    The question registration asks before superseding a sign-up. It is
    :func:`mailbox_control_proven` plus ``last_login``, and expressed that way on
    purpose: the weaker predicate must never be *narrower* than the stronger one, or an
    account social login refuses to touch could still be destroyed by a registration.

    ``last_login`` belongs here and nowhere else. It cannot say whose account this is,
    but it does say the account has been worked in, and that is enough to refuse to
    delete it.

    Args:
        user (AbstractBaseUser): Owner of the address under evaluation.
        reserve_invitations (bool): See :func:`mailbox_control_proven`.

    Returns:
        bool: ``True`` unless the account is a sign-up that was never confirmed.
    """
    if user is None:
        return True
    if user.last_login is not None:
        return True
    return mailbox_control_proven(user, reserve_invitations)


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


def resolve_email_for_provider(email):
    """
    Who holds ``email``, for a caller an identity provider has just proved control of it to.

    :func:`resolve_email` with a stronger predicate is not enough, because this caller
    has **three** outcomes to tell apart rather than two, and the third one is the whole
    point: an account that has been used but whose address was never confirmed is
    neither somebody the provider may be signed into (nothing proves it is the same
    person) nor an abandoned sign-up that may be deleted (somebody has been working in
    it). Folding it into either bucket trades one loss for the other.

    Args:
        email (str): Address to resolve. Matched as :func:`resolve_email` matches it.

    Returns:
        tuple: ``(owner, occupied, abandoned)``, one query per address.

        * ``owner`` -- control of the address was demonstrated. The provider is the same
          person; connect to this account.
        * ``occupied`` -- accounts in use whose address is unconfirmed. Neither linkable
          nor removable: refuse, and let the owner confirm the address they already have
          the mail for. Whoever merely typed the address into a sign-up form cannot.
        * ``abandoned`` -- never confirmed and never used. Free to supersede, exactly as
          registration supersedes them.

        The last two are empty whenever ``owner`` is set.
    """
    occupied, abandoned = [], []
    for address in EmailAddress.objects.filter(email=email.lower()).select_related('user'):
        user = address.user
        if address.verified or mailbox_control_proven(user):
            return user, [], []
        # Control is unproven, so `account_is_claimed` is what is left to ask -- and by
        # its own definition all that remains of it here is `last_login`.
        (occupied if user.last_login is not None else abandoned).append(user)
    return None, occupied, abandoned


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
