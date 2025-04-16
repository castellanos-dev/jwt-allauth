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
