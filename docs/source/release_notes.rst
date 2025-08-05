Release Notes
=============

Version 1.0.3
-------------

Released: August 5, 2025

New Features
~~~~~~~~~~~~

- New :func:`~jwt_allauth.utils.load_user` decorator that loads the complete user object from the database for stateless JWT authentication.

Bug Fixes
~~~~~~~~~

- Improved security for token refresh operations


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
