from rest_framework.permissions import BasePermission as DefaultBasePermission

from django.conf import settings
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
