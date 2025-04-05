from rest_framework.permissions import BasePermission as DefaultBasePermission

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
        if not isinstance(self.accepted_roles, list):
            raise ValueError('`accepted_roles` must be a list.')
        if hasattr(request, 'auth'):
            if request.auth and 'role' in request.auth:
                if request.auth['role'] in self.accepted_roles + [STAFF_CODE, SUPER_USER_CODE]:
                    return True
        return False


class BasePermissionStaffExcluded(DefaultBasePermission):
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
        if not isinstance(self.accepted_roles, list):
            raise ValueError('`accepted_roles` must be a list.')
        if hasattr(request, 'auth'):
            if request.auth and 'role' in request.auth:
                if request.auth['role'] in self.accepted_roles:
                    return True
        return False
