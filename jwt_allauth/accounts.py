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

from allauth.account.models import EmailAddress


def account_is_claimed(user) -> bool:
    """
    Whether somebody has already established ownership of ``user``.

    Args:
        user (AbstractBaseUser): Owner of the address under evaluation.

    Returns:
        bool: ``True`` unless the account is a sign-up that was never confirmed.
    """
    if user is None:
        return True
    if user.is_staff or user.is_superuser:
        return True
    if user.last_login is not None:
        return True
    return EmailAddress.objects.filter(user=user, verified=True).exists()


def resolve_email(email):
    """
    Who holds ``email``, in one query.

    Both callers need the same two facts about an address -- whether somebody has
    established ownership of it, and which accounts may be superseded if nobody has --
    and both used to ask twice, then throw the rows away and ask again to find out who
    the owner was. Asking once also settles a question two lookups cannot agree on: with
    ``ACCOUNT_UNIQUE_EMAIL`` off, several accounts can hold one address, and a second
    unordered query may return a different row from the one that reached the verdict.

    Args:
        email (str): Normalized address to resolve.

    Returns:
        tuple: ``(owner, superseded)``. ``owner`` is the account that established
        ownership, or ``None`` when nobody has; ``superseded`` lists the unclaimed
        accounts holding the address, and is empty when ``owner`` is set or the address
        is free.
    """
    accounts = []
    for address in EmailAddress.objects.filter(email__iexact=email).select_related('user'):
        if address.verified or account_is_claimed(address.user):
            return address.user, []
        accounts.append(address.user)
    return None, accounts


def superseded_accounts(email):
    """
    Accounts a registration for ``email`` is allowed to take over.

    An address is only up for grabs while nobody has proven control over it: it
    must be unverified and belong to an account that was never used. Anything
    else -- a verified address, a secondary address of an established account --
    is off limits, no matter that it is still pending confirmation.

    Args:
        email (str): Normalized address requested by the caller.

    Kept as the shape :class:`~jwt_allauth.registration.serializers.RegisterSerializer`
    exposes and a subclass may override. :func:`resolve_email` is the one that answers
    both halves at once.

    Returns:
        list|None: Pending accounts to supersede, empty when the address is
        free, or ``None`` when the address is taken.
    """
    owner, superseded = resolve_email(email)
    return None if owner is not None else superseded
