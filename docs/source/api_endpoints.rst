API endpoints
=============

Authentication
--------------

**/login/** (POST)
^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``email``
     - User's email address.
   * - Body (JSON)
     - ``password``
     - User's password.

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``access``
     - JWT access token.
   * - Cookie (HTTP-only)
     - ``refresh_token``
     - JWT refresh token, stored by default in the ``refresh_token`` cookie.
   * - Body (JSON, optional)
     - ``mfa_required``
     - When MFA is enabled and the user has it configured. The response contains a ``challenge_id`` instead of tokens so you can complete login via the MFA verification endpoints.
   * - Body (JSON, optional)
     - ``mfa_setup_required``
     - When MFA mode is REQUIRED but the user has not set it up yet. The response contains a ``setup_challenge_id`` to bootstrap MFA setup.

**URL Name:** ``rest_login``

.. note:: Django Rest Framework throttling enabled, see: https://www.django-rest-framework.org/api-guide/throttling/

**/refresh/** (POST)
^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Cookie (HTTP-only, default)
     - ``refresh_token``
     - Refresh token read automatically from the ``refresh_token`` cookie when ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = True`` (default).
   * - Body (JSON, optional)
     - ``refresh``
     - Refresh token sent explicitly in the request body when you are not using cookies (``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``).

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``access``
     - New JWT access token.
   * - Cookie (HTTP-only, default)
     - ``refresh_token``
     - New refresh token stored in the ``refresh_token`` cookie when cookies are enabled.
   * - Body (JSON, optional)
     - ``refresh``
     - New refresh token returned in the response body when cookies are disabled.

**URL Name:** ``token_refresh``

**/logout/** (POST) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Cookie (HTTP-only, default)
     - ``refresh_token``
     - Refresh token taken automatically from the ``refresh_token`` cookie when ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = True``.
   * - Body (JSON, optional)
     - ``refresh``
     - Refresh token to invalidate when you are not using cookies (``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``).

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``200 OK``
     - User successfully logged out and the refresh token is revoked.

**URL Name:** ``rest_logout``

**/logout-all/** (POST) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - N/A
     - No request body or query parameters.

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``200 OK``
     - User successfully logged out from all devices.

**/password/reset/** (POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``email``
     - Email address to send the reset link to.

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``200 OK``
     - JSON response with a ``detail`` message indicating that the reset e-mail has been sent.

**URL Name:** ``rest_password_reset``

.. note:: Django Rest Framework throttling enabled, see: https://www.django-rest-framework.org/api-guide/throttling/

.. warning:: Requires an email server configured.

**/password/reset/confirm/<str:uidb64>/<str:token>/** (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - HTML page
     - Redirects to the UI configured by ``PASSWORD_RESET_REDIRECT`` or renders the default password reset form.

**URL Name:** ``password_reset_confirm``

.. note:: uid and token are sent in email after calling ``/password/reset/``

**/password/reset/default/** (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - HTML page
     - Renders the default password reset form.

**URL Name:** ``default_password_reset``

.. note:: Used when ``PASSWORD_RESET_REDIRECT`` is not configured.

**/password/reset/complete/** (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - HTML page
     - Renders the password reset complete page.

**URL Name:** ``jwt_allauth_password_reset_complete``

.. note:: Used when ``PASSWORD_RESET_REDIRECT`` is not configured.

**/password/reset/set-new/** (POST) ``[Cookie]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Cookie (HTTP-only)
     - ``password_reset_access_token``
     - One-time access token set as a secure cookie when the user follows the reset link.
   * - Body (JSON)
     - ``new_password1``
     - New password.
   * - Body (JSON)
     - ``new_password2``
     - Password confirmation.

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``200 OK``
     - Password updated successfully. Returns new JWT tokens and a ``detail`` message.

**URL Name:** ``password_reset_confirm``

**/password/change/** (POST) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``new_password1``
     - New password.
   * - Body (JSON)
     - ``new_password2``
     - Password confirmation.
   * - Body (JSON, optional)
     - ``old_password``
     - Current password (required if ``OLD_PASSWORD_FIELD_ENABLED = True``).

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``200 OK``
     - Password changed successfully. Optionally logs the user out of other sessions when ``LOGOUT_ON_PASSWORD_CHANGE = True``.

**URL Name:** ``rest_password_change``

.. note:: ``OLD_PASSWORD_FIELD_ENABLED = True`` to use old_password (default).
.. note:: ``LOGOUT_ON_PASSWORD_CHANGE = True`` to logout from the remaining sessions.

**/user/** (GET, PUT, PATCH) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request (PUT/PATCH)**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``email``
     - User email address.
   * - Body (JSON, optional)
     - ``first_name``
     - User's first name.
   * - Body (JSON, optional)
     - ``last_name``
     - User's last name.

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``email``
     - User's email address.
   * - Body (JSON)
     - ``first_name``
     - User's first name.
   * - Body (JSON)
     - ``last_name``
     - User's last name.

**URL Name:** ``rest_user_details``

Registration
------------

**/registration/** (POST)
^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``email``
     - Email address for the new user.
   * - Body (JSON)
     - ``password1``
     - Password.
   * - Body (JSON)
     - ``password2``
     - Password confirmation.
   * - Body (JSON, optional)
     - ``first_name``
     - First name.
   * - Body (JSON, optional)
     - ``last_name``
     - Last name.

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON, optional)
     - ``key``
     - Authentication token when email verification is disabled.
   * - Body (JSON)
     - ``email``
     - Registered email address.
   * - Body (JSON)
     - ``detail``
     - Message indicating that a verification e-mail has been sent when email verification is enabled.

**URL Name:** ``rest_register``

.. note:: Disabled when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True`` (the open registration endpoint is removed in admin-managed mode).

**/registration/user-register/** (POST) ``[Admin role]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``email``
     - Email address for the new user.
   * - Body (JSON)
     - ``role``
     - User role to assign to the new user.
   * - Body (JSON, optional)
     - ``first_name``
     - First name.
   * - Body (JSON, optional)
     - ``last_name``
     - Last name.

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``201 Created``
     - Verification e-mail sent to the invited user.

**URL Name:** ``rest_user_register``

.. note:: Enabled when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``. Keeps the default ``/registration/`` endpoint unchanged unless you enable this setting.

**/registration/verification/<str:key>/** (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - Redirect / HTML page
     - Redirects to the UI configured by ``EMAIL_VERIFIED_REDIRECT`` or renders the verified page.

**URL Name:** ``account_confirm_email``

.. note:: Disabled when ``EMAIL_VERIFICATION = False``.

**/registration/set-password/** (POST) ``[Cookie]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Cookie (HTTP-only)
     - ``set_password_access_token``
     - One-time access token set as a secure cookie after the invited user clicks the verification link.
   * - Body (JSON)
     - ``new_password1``
     - Password.
   * - Body (JSON)
     - ``new_password2``
     - Password confirmation.

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``200 OK``
     - Password set successfully. Returns JWT tokens or an MFA setup challenge depending on the MFA configuration.

**URL Name:** ``rest_set_password``

.. note:: Only available when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``. This endpoint is reached after the invited user clicks the verification link. The GET verification drops a one-time access token in the ``set_password_access_token`` cookie and redirects to the UI configured by ``PASSWORD_SET_REDIRECT``. Throttled with ``UserRateThrottle`` by default.

**/registration/account_email_verification_sent/** (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - HTML page
     - Renders the email verification sent notification page.

**URL Name:** ``account_email_verification_sent``

.. note:: Disabled when ``EMAIL_VERIFICATION = False``.

**/registration/verified/** (GET)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - HTML page
     - Renders the email verified confirmation page.

**URL Name:** ``jwt_allauth_email_verified``

.. note:: Disabled if ``EMAIL_VERIFIED_REDIRECT`` is defined or ``EMAIL_VERIFICATION = False``.

Multi-Factor Authentication (MFA)
----------------------------------

.. note:: Requires ``allauth.mfa`` in ``INSTALLED_APPS`` of your Django project and database migrations applied.

**/mfa/setup/** (POST) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - N/A
     - No request body. The authenticated user (or MFA setup challenge) is used to determine which account to configure.

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``provisioning_uri``
     - OTPAuth URI for QR code generation.
   * - Body (JSON)
     - ``secret``
     - Base32-encoded secret key.
   * - Body (JSON)
     - ``qr_code``
     - SVG formatted QR code image.

**URL Name:** ``mfa_setup``

**/mfa/activate/** (POST) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``code``
     - TOTP code from the authenticator app.
   * - Body (JSON, optional)
     - ``setup_challenge_id``
     - Challenge ID used in MFA bootstrap flows (login or registration) when MFA mode is ``required``.

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``recovery_codes``
     - List of one-time recovery codes.
   * - Body (JSON, optional)
     - ``success``
     - Indicates successful activation (always ``True`` on success).
   * - Body (JSON, optional)
     - ``access``
     - Access token issued when MFA mode is ``required`` and activation is performed using ``setup_challenge_id``.
   * - Body (JSON, optional)
     - ``refresh``
     - Refresh token issued when MFA mode is ``required`` and activation is performed using ``setup_challenge_id`` (may be delivered via HTTP-only cookie depending on settings).

**URL Name:** ``mfa_activate``

**/mfa/verify/** (POST)
^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``challenge_id``
     - MFA challenge ID from the login attempt.
   * - Body (JSON)
     - ``code``
     - TOTP code from the authenticator app.

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``access``
     - JWT access token.
   * - Cookie (HTTP-only)
     - ``refresh_token``
     - JWT refresh token set in the ``refresh_token`` cookie (by default).

**URL Name:** ``mfa_verify``

**/mfa/verify-recovery/** (POST)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``challenge_id``
     - MFA challenge ID from the login attempt.
   * - Body (JSON)
     - ``recovery_code``
     - One-time recovery code.

**Response**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``access``
     - JWT access token.
   * - Cookie (HTTP-only)
     - ``refresh_token``
     - JWT refresh token set in the ``refresh_token`` cookie (by default).

**URL Name:** ``mfa_verify_recovery``

**/mfa/deactivate/** (POST) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Location
     - Field
     - Description
   * - Body (JSON)
     - ``password``
     - User's password for confirmation.

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Status
     - Description
   * - ``200 OK``
     - MFA TOTP authenticator (and recovery codes) deactivated for the user.

**URL Name:** ``mfa_deactivate``

**/mfa/authenticators/** (GET) ``[Authenticated]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Request**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - N/A
     - No request body or query parameters.

**Response**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Location
     - Description
   * - Body (JSON)
     - Array of authenticator objects with details about enabled MFA devices.

**URL Name:** ``mfa_authenticators``

.. note:: MFA TOTP can be configured with the ``JWT_ALLAUTH_MFA_TOTP_MODE`` setting:

   - ``'disabled'`` (default): MFA endpoints return 403 Forbidden when accessed.
   - ``'optional'``: Users can set up MFA but it's not required during login.
   - ``'required'``: Users must set up MFA and provide TOTP code during login. Deactivation is blocked.
