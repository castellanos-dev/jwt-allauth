Admin-managed registration
==========================

Overview
--------

When ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True`` the library enables a closed registration flow where existing admins invite users. In this mode, ``EMAIL_VERIFICATION`` is ignored: the email is verified during the verification GET, and not at the password set step.

- Admin creates the user via ``POST /registration/user-register/``.
- The invited user receives a verification email.
- Upon clicking the verification link (``GET /registration/verification/<key>/``), a one-time access token is stored in an HTTP-only cookie and the user is redirected to the UI path configured in ``PASSWORD_SET_REDIRECT``.
- The UI submits ``POST /registration/set-password/`` with ``new_password1``/``new_password2`` to set the password and receive tokens.

Endpoints
---------

- ``POST /registration/user-register/`` (name: ``rest_user_register``) — Allowed to roles defined by ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES`` (defaults to ``[STAFF_CODE, SUPER_USER_CODE]``).
- ``GET /registration/verification/<key>/`` (name: ``account_confirm_email``) — Confirms the email and drops a ``set_password_access_token`` cookie when admin-managed is enabled.
- ``POST /registration/set-password/`` (name: ``rest_set_password``) — Reads the one-time token from cookie, sets password, returns tokens. Throttled with ``UserRateThrottle``.

Payloads
--------

- Admin creates a user:

  .. code-block:: json

     {
       "email": "writer@demo.com",
       "role": 300,
       "first_name": "Optional",
       "last_name": "Optional"
     }

- Set password after verification:

  .. code-block:: json

     {
       "new_password1": "********",
       "new_password2": "********"
     }

Behavior
--------

- Duplicate email:
  - If an existing verified ``EmailAddress`` is found for the email, registration fails with 400 on ``email``.
  - If only non-verified entries exist, they are removed and a new user is created (previous user loses the associated ``EmailAddress``), allowing coexistence.

- Response from ``user-register`` is a 201 with an empty body.

Settings
--------

- ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` (default: ``False``)
- ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES`` (default: ``[STAFF_CODE, SUPER_USER_CODE]``) — list of role codes allowed to register users.
- ``PASSWORD_SET_REDIRECT`` — UI path for the set-password form
- ``PASSWORD_SET_COOKIE_HTTP_ONLY`` (default: ``True``)
- ``PASSWORD_SET_COOKIE_SECURE`` (default: ``not DEBUG``)
- ``PASSWORD_SET_COOKIE_SAME_SITE`` (default: ``'Lax'``)
- ``PASSWORD_SET_COOKIE_MAX_AGE`` (default: ``3600 * 24`` seconds)

Permissions
-----------

- ``RegisterUsersPermission`` — grants access to ``user-register`` when the requester's role is in ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES``. Defaults to allowing ``STAFF_CODE`` and ``SUPER_USER_CODE``.

Email verification behavior
---------------------------

- The verification GET confirms the email in admin-managed mode and issues a one-time token, then redirects to the password set UI.
- The set-password endpoint does not alter email verification status.
