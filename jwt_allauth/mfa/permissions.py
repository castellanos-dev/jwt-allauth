"""
Permissions for MFA endpoints.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import permissions


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

        data = cache.get(f"mfa_setup_challenge:{setup_challenge_id}")
        if not data:
            return False

        user_id = data.get("user_id")
        if not user_id:
            return False

        User = get_user_model()
        try:
            request.mfa_setup_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return False

        return True
