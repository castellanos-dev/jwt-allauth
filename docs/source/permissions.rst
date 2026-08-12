View Permissions
----------------

JWT Allauth enables role-based authentication for API views. The user model includes an integer field representing the
assigned role, which is embedded in both refresh and access tokens. This allows authentication to occur without
requiring database queries during the process.

The default role codes are:

    - STAFF_CODE: 1000
    - SUPER_USER_CODE: 900
    - USER_CODE: 0

New users are assigned the default role value of 0.

Because the role travels inside the tokens, a role change is not visible to the permission classes until a new token is
issued. The refresh endpoint regenerates the role claim from the database on every rotation, so the change applies at
the latest on the next refresh (i.e. within the lifetime of the access token). To revoke privileges immediately, delete
the user's entries in the refresh token whitelist, which forces a new login.

Usage example
"""""""""""""

The APIs can be restricted to authenticated users using the ``IsAuthenticated`` class.

.. code-block:: python

    from rest_framework.permissions import IsAuthenticated

    class UserDetailsView(RetrieveUpdateAPIView):
        serializer_class = UserDetailsSerializer
        permission_classes = (IsAuthenticated,)

A permission class can be created in the following by extending the :class:`~jwt_allauth.permissions.BasePermission`
and :class:`~jwt_allauth.permissions.BasePermissionStaffExcluded` classes. The ``accepted_roles`` attribute should
included all the roles allowed for the corresponding permission.

.. code-block:: python

    from jwt_allauth.permissions import BasePermission

    class CreateUserPermission(BasePermission):
        accepted_roles = [700]


.. code-block:: python

    from permissions import CreateUserPermission

    class UserDetailsView(RetrieveUpdateAPIView):
        serializer_class = UserDetailsSerializer
        permission_classes = (CreateUserPermission,)

.. note:: Login, refresh, registration, email confirmation and the password reset flow declare their
   own permission classes, so a restrictive ``DEFAULT_PERMISSION_CLASSES`` (e.g. ``IsAuthenticated``)
   in ``REST_FRAMEWORK`` does not lock the endpoints a user must reach before holding a token.

Requiring a verified email address
""""""""""""""""""""""""""""""""""

:class:`~jwt_allauth.permissions.IsEmailVerified` reads the ``email_verified`` claim, which travels
in the tokens next to the role and is re-read from the database on every rotation. Nothing is read
from the database at request time, so it costs the same as the role check.

.. code-block:: python

    from jwt_allauth.permissions import IsEmailVerified

    class InviteTeammateView(APIView):
        permission_classes = [IsEmailVerified]

It composes with the role permissions through DRF's operators, so *regular and verified* needs no
class of its own:

.. code-block:: python

    permission_classes = [CreateUserPermission & IsEmailVerified]

Which endpoints it guards is the project's decision — the package guards none by itself. It is what
makes ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` worth having: the account is usable from sign-up,
so verification governs features rather than the session. A token that predates the claim, or that
has not been rotated since the address was confirmed, is denied and never wrongly granted; the
holder gets it back by calling ``/refresh/``. See :doc:`email_verification`.
