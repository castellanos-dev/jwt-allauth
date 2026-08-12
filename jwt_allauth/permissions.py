from rest_framework.permissions import BasePermission as DefaultBasePermission

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from jwt_allauth.constants import EMAIL_VERIFIED_CLAIM
from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE


class BasePermission(DefaultBasePermission):
    """
    Custom base permission class for role-based access control using JWT claims.

    Extends DRF's BasePermission to check for roles in the JWT payload.
    **Automatically grants access to staff and superusers** in addition to specified roles.

    Behavior:

        - Checks JWT payload for 'role' claim
        - Allows access if role is in accepted_roles, STAFF_CODE, or SUPER_USER_CODE
        - Requires request.auth to contain decoded JWT payload
        - Staff and superusers (STAFF_CODE/SUPER_USER_CODE) always have access

    Class Attributes:
        accepted_roles (list): Required list of role codes that are allowed access.
                               Must be initialized in subclasses.

    Raises:
        ValueError: If accepted_roles is not properly initialized as a list
    """
    accepted_roles = None

    def _check_role_permission(self, request, include_staff=True):
        """
        Internal method to check role-based permissions.

        Args:
            request (Request): DRF request object containing JWT in auth attribute
            include_staff (bool): Whether to include staff and superuser roles in the check

        Returns:
            bool: True if authorized, False otherwise
        """
        if not isinstance(self.accepted_roles, list):
            raise ValueError('`accepted_roles` must be a list.')

        if not hasattr(request, 'auth'):
            return False

        if not request.auth or 'role' not in request.auth:
            return False

        roles_to_check = self.accepted_roles
        if include_staff:
            roles_to_check = self.accepted_roles + [STAFF_CODE, SUPER_USER_CODE]

        return request.auth['role'] in roles_to_check

    def has_permission(self, request, view):
        """
        Determine if the request should be permitted based on JWT roles.

        Args:
            request (Request): DRF request object containing JWT in auth attribute
            view (View): DRF view being accessed

        Returns:
            bool: True if authorized, False otherwise
        """
        return self._check_role_permission(request, include_staff=True)


class BasePermissionStaffExcluded(BasePermission):
    """
    Custom base permission class for role-based access control using JWT claims.

    Extends DRF's BasePermission to check for roles in the JWT payload.

    Behavior:

        - Checks JWT payload for 'role' claim
        - Allows access if role is in accepted_roles, STAFF_CODE, or SUPER_USER_CODE
        - Requires request.auth to contain decoded JWT payload

    Class Attributes:
        accepted_roles (list): Required list of role codes that are allowed access.
                               Must be initialized in subclasses.

    Raises:
        ValueError: If accepted_roles is not properly initialized as a list
    """
    accepted_roles = None

    def has_permission(self, request, view):
        """
        Determine if the request should be permitted based on JWT roles.

        Args:
            request (Request): DRF request object containing JWT in auth attribute
            view (View): DRF view being accessed

        Returns:
            bool: True if authorized, False otherwise

        Raises:
            ValueError: If accepted_roles is not a list
        """
        return self._check_role_permission(request, include_staff=False)


class IsEmailVerified(DefaultBasePermission):
    """
    Allows access only to tokens whose account has a confirmed e-mail address.

    Reads the ``email_verified`` claim, which
    :meth:`jwt_allauth.tokens.tokens.RefreshToken.set_email_verified` writes when the
    session starts and refreshes on every rotation. Nothing is read from the database:
    the check costs the same as the role check next to it.

    This is the gate that makes ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` worth
    having. With ``'optional'`` the account is usable from sign-up, so verification has
    to govern features rather than the session; which endpoints it governs is the
    project's decision, not this package's.

    Behavior:

        - Denies when the token carries no ``email_verified`` claim, which is the case
          for tokens minted before the claim existed. The claim only ever turns on, so
          a stale token denies and never grants: it fails closed by construction. The
          holder gets it back by calling ``/refresh/``.
        - Composes with the role permissions through DRF's operators, so *regular and
          verified* needs no class of its own:

          .. code-block:: python

              from jwt_allauth.permissions import IsEmailVerified

              class RegularUserPermission(BasePermission):
                  accepted_roles = [REGULAR_USER_CODE]

              class MyView(APIView):
                  permission_classes = [RegularUserPermission & IsEmailVerified]
    """
    message = _('E-mail address is not verified.')

    def has_permission(self, request, view):
        """
        Determine if the request should be permitted based on the verification claim.

        Args:
            request (Request): DRF request object containing JWT in auth attribute
            view (View): DRF view being accessed

        Returns:
            bool: True if the token states that the address is verified, False otherwise
        """
        auth = getattr(request, 'auth', None)
        if not auth:
            return False
        if EMAIL_VERIFIED_CLAIM not in auth:
            return False
        return bool(auth[EMAIL_VERIFIED_CLAIM])


class RegisterUsersPermission(BasePermissionStaffExcluded):
    """
    Allows user registration access when the requester's role is included in the allowed roles setting.

    Settings:
        JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES: list of integers (role codes).
            Defaults to [STAFF_CODE, SUPER_USER_CODE].
    """
    accepted_roles = []  # computed per request

    def has_permission(self, request, view):
        # Resolve allowed roles from settings with sensible defaults
        allowed = getattr(
            settings,
            'JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES',
            [STAFF_CODE, SUPER_USER_CODE]
        )
        # Ensure list type
        self.accepted_roles = list(allowed)
        # Do NOT auto-include staff/superuser here; the setting is authoritative
        return super().has_permission(request, view)
