"""
The socialaccount adapter this library installs when the project has none of its own.

It exists for two decisions allauth leaves open and that this library has already made
elsewhere: who may register, and what has to remain true after a provider is removed.

The role of a new account is deliberately not touched here. allauth builds the user
through the account adapter's ``new_user()``, a bare model instance, so the default of
the ``role`` field applies and :meth:`~jwt_allauth.tokens.tokens.RefreshToken.set_user_role`
reads whatever that field holds -- the same path an admin-created account takes.
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class JWTAllAuthSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Social account adapter aligned with this library's registration and session rules.
    """

    def is_open_for_signup(self, request, sociallogin) -> bool:
        """
        Whether an unrecognised provider account may become a new user.

        ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` closes open registration --
        :class:`~jwt_allauth.registration.views.RegisterView` answers ``404`` under it --
        and a provider account nobody has seen before is a registration like any other.
        Leaving this to the default would open a way in that the registration endpoint
        was explicitly shut.
        """
        if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
            return False
        return super().is_open_for_signup(request, sociallogin)

    def validate_disconnect(self, account, accounts) -> None:
        """
        Refuse to remove the last way into an account.

        allauth's implementation is a no-op, and ``save_user`` gives an account created
        through a provider an unusable password. Removing its only provider would
        therefore lock its owner out for good: there is no password to reset, because
        there is no password.

        Args:
            account (SocialAccount): The connection about to be removed.
            accounts (list): Every connection the account currently holds.

        Raises:
            django.core.exceptions.ValidationError: When ``account`` is the only
                connection and the user has no usable password.
        """
        super().validate_disconnect(account, accounts)
        if len(accounts) > 1:
            return
        if not account.user.has_usable_password():
            raise ValidationError(_("This is the only way to sign in to this account."))
