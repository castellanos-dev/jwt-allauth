"""
Permissions for MFA endpoints.
"""
from rest_framework import permissions

from jwt_allauth.mfa.storage import get_setup_challenge_user


class IsAuthenticatedOrHasMFASetupChallenge(permissions.BasePermission):
    """
    Allows access if:
    - The user is authenticated via JWT (IsAuthenticated), or
    - The request provides a valid setup_challenge_id for MFA bootstrap.

    In the bootstrap case (setup_challenge_id), attaches request.mfa_setup_user
    with the user object loaded from the challenge data.

    This permission enables users to access /mfa/setup/ and /mfa/activate/
    endpoints during the MFA bootstrap process without a full JWT session token.
    The setup_challenge_id is issued by /login/ when MFA is REQUIRED but not yet configured.
    """

    def has_permission(self, request, view):
        # Case 1: Normal JWT authentication
        if request.user and request.user.is_authenticated:
            return True

        # Case 2: Bootstrap MFA via setup_challenge_id
        setup_challenge_id = request.data.get("setup_challenge_id")
        if not setup_challenge_id:
            return False

        user = get_setup_challenge_user(setup_challenge_id)
        if not user:
            return False

        request.mfa_setup_user = user
        return True
