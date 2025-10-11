Release Notes
=============

Version 1.1.1
-------------

Released: October 11, 2025

Breaking Change
~~~~~~~~~~~~~~~

- ``JWT_ALLAUTH_USER_ATTRIBUTES`` now expects a dictionary mapping output claim names to user attribute paths (e.g., ``{"organization_id": "organization.id"}``) instead of a list of paths. This change prevents duplicate final attribute names (e.g., multiple ``id`` keys) in JWT payloads. The previous list format is still accepted for backward compatibility, but it is deprecated and may be removed in a future release.

Version 1.1.0
-------------

Released: October 7, 2025

New Features
~~~~~~~~~~~~

- Added support for including additional user attributes in refresh tokens via the ``JWT_ALLAUTH_USER_ATTRIBUTES`` setting, allowing flexible configuration of user data included in JWT payloads while maintaining the existing role assignment logic.

Bug Fixes
~~~~~~~~~

- Fixed API endpoints that incorrectly required refresh token in request payload when ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` was enabled, now properly extracting refresh tokens from cookies when configured.

- Fixed a bug that caused migrations not to run correctly in some situations.

Version 1.0.3
-------------

Released: August 5, 2025

New Features
~~~~~~~~~~~~

- New :func:`~jwt_allauth.utils.load_user` decorator that loads the complete user object from the database for stateless JWT authentication.
- Added ``JWT_ALLAUTH_COLLECT_USER_AGENT`` setting to control user agent data collection during token refresh.
- Added support for refresh tokens via HTTP cookies with the new ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` setting.
- Enhanced token refresh security by moving user agent data collection from request payload to server-side context.
- Compatibility with ``django-allauth`` 65.10.0, ``djangorestframework-simplejwt`` 5.5.1, and ``djangorestframework``  3.16.0.

Bug Fixes
~~~~~~~~~

- Improved security for token refresh operations
- Fixed a bug that caused migrations not to run correctly in some situations.


Version 1.0.2
-------------

Released: April 16, 2025

This release introduces significant improvements to the role management system and authentication configuration.

New Features
~~~~~~~~~~~~

- Added automatic role assignment in ``UserManager``:

    - ``create_superuser`` now automatically sets the role to ``STAFF_CODE``
    - ``create_user`` automatically assigns roles based on user flags:
        - ``STAFF_CODE`` for staff users
        - ``SUPER_USER_CODE`` for superusers

- Added database constraints to ensure role consistency:

    - Staff users must have ``STAFF_CODE`` role
    - Superusers must have ``SUPER_USER_CODE`` role

Minor Bug Fixes
~~~~~~~~~~~~~~~

- Automatic configuration of ``DEFAULT_AUTHENTICATION_CLASSES`` was not working when using addiotional ``REST_FRAMEWORK`` settings.
