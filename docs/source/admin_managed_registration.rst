Admin-managed registration
==========================

Overview
--------

When ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True`` the library enables a closed registration flow where existing admins invite users. In this mode, the ``EMAIL_VERIFICATION`` setting is effectively ignored for invited users: the email is always verified during the verification ``GET`` step, never at the password-set step.

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

Email templates
---------------

- The verification email sent for admin-managed invitations uses a dedicated template
  whose defaults are:

  - Subject: ``email/admin_invite/email_subject.txt``
  - HTML body: ``email/admin_invite/email_message.html``

- You can override these by configuring ``JWT_ALLAUTH_TEMPLATES`` with
  ``ADMIN_EMAIL_VERIFICATION_SUBJECT`` and ``ADMIN_EMAIL_VERIFICATION``. See
  :doc:`configuration.settings_py` for details.

MFA REQUIRED Integration
------------------------

When ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'`` and ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``, the admin-managed registration flow is extended to **enforce MFA setup** and provides **immediate token issuance after MFA activation**. This mirrors the MFA bootstrap behavior described in :doc:`mfa_totp`.

**Flow with MFA REQUIRED:**

1. Admin creates user via ``POST /registration/user-register/`` → User created, no tokens
2. User receives verification email
3. User clicks verification link → One-time token issued in cookie
4. User sets password via ``POST /registration/set-password/`` → **Returns MFA setup challenge** instead of tokens:

   .. code-block:: json

       {
           "mfa_setup_required": true,
           "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
           "detail": "Password set. Please configure MFA to complete registration."
       }

5. User accesses ``POST /mfa/setup/`` with ``setup_challenge_id`` (no authentication required)
6. User accesses ``POST /mfa/activate/`` with ``setup_challenge_id`` and TOTP code
7. **Tokens are issued** after successful MFA activation (using the same response helper as login, respecting cookie configuration)
8. User can now login normally

**Key Differences:**

- ``set-password`` endpoint returns ``mfa_setup_required`` + ``setup_challenge_id`` instead of tokens
- Users cannot receive tokens until MFA is configured
- The ``setup_challenge_id`` allows temporary access to MFA setup endpoints without full authentication
- **After successful MFA activation** (``POST /mfa/activate/``), tokens are issued immediately (unlike self-service registration, where users must re-login)
- This ensures all users go through MFA setup before gaining any access, preventing security bypasses
- Users immediately have access after MFA activation without needing to re-login

**Settings Impact:**

The following settings continue to work as expected:
- ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` — Controls token delivery method after MFA activation (respects this setting)
- ``PASSWORD_SET_COOKIE_*`` — Controls one-time token cookie during password setup
- ``JWT_ALLAUTH_MFA_TOTP_MODE`` — Must be set to ``'required'`` for this behavior
- ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` — Must be set to ``True`` for tokens to be issued immediately after MFA activation

**Important: Immediate Token Issuance**

When both ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'`` and ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``:

- ``/mfa/activate/`` endpoint returns **tokens immediately** after successful TOTP verification
- This means users do **not** need to re-login after MFA setup
- This improves user experience for invited/admin-managed workflows by providing seamless onboarding

This behavior is **different from self-service registration**, where ``/mfa/activate/`` returns only recovery codes and the user must re-login to obtain tokens.


See also
--------

- :doc:`mfa_totp` — full MFA TOTP configuration and flows (login, self-service registration, and admin-managed registration).
- :doc:`configuration.settings_py` — details on ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION``, ``JWT_ALLAUTH_MFA_TOTP_MODE``, cookie settings, and template overrides.
