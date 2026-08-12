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

.. note:: Django Rest Framework throttling enabled, on top of the ``DEFAULT_THROTTLE_CLASSES`` of the project, see: https://www.django-rest-framework.org/api-guide/throttling/ and :doc:`configuration.settings_py`

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

.. note::

    When ``JWT_ALLAUTH_SESSION_LIFETIME`` is configured (disabled by default), rotation stops extending the
    session once that limit is reached: the session is revoked and the endpoint responds ``401`` with code
    ``session_expired``, so the client must authenticate again.

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

.. note:: Django Rest Framework throttling enabled, on top of the ``DEFAULT_THROTTLE_CLASSES`` of the project, see: https://www.django-rest-framework.org/api-guide/throttling/ and :doc:`configuration.settings_py`

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

.. note:: Opened by an anonymous user, so the view declares ``AllowAny`` and is not affected by the
   project's ``DEFAULT_PERMISSION_CLASSES``.

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
   * - Header
     - ``X-CSRFToken``
     - CSRF token, from the ``csrftoken`` cookie set on the same redirect. Not required when ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF = False``.
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
   * - ``401 Unauthorized``
     - The cookie is missing, expired, already used, or the account it names has been deactivated or deleted.
   * - ``403 Forbidden``
     - Missing or invalid CSRF token.

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
     - Password changed successfully. With ``LOGOUT_ON_PASSWORD_CHANGE = True`` (default) every session is revoked, the caller's included, and the response carries a replacement session: ``access`` in the body and the refresh token as a cookie (or in the body when ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``). With it set to ``False`` nothing is revoked and the response holds only ``detail``.

**URL Name:** ``rest_password_change``

.. note:: ``OLD_PASSWORD_FIELD_ENABLED = True`` to use old_password (default).

.. note::

    **The caller's session goes too.** A password change is a handover of the account, so with
    ``LOGOUT_ON_PASSWORD_CHANGE = True`` it takes down every session, every capability still
    outstanding (unused reset and set-password links, e-mail confirmation tokens, MFA setup
    challenges) and every unconfirmed secondary address queued up behind the primary one. Sparing
    the session that asked for the change would spare it for whoever is holding it. The client
    replaces its tokens with the ones in the response; the refresh token cookie is overwritten for
    it. The old refresh token stops rotating at once, and any access token already issued stays
    usable until it expires unless ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`` is on.

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
   * - Body (JSON)
     - ``detail``
     - Message indicating that a verification e-mail has been sent. Only when verification is mandatory.
   * - Body (JSON, optional)
     - ``refresh``
     - Refresh token. Always present unless enumeration prevention withholds it (see the note below). Born disabled, and unusable until the address is confirmed, while verification is mandatory.
   * - Body (JSON, optional)
     - ``access``
     - Access token. Only when verification is not mandatory, i.e. ``EMAIL_VERIFICATION = False`` or ``ACCOUNT_EMAIL_VERIFICATION = 'optional'``.
   * - Body (JSON, optional)
     - ``mfa_setup_required``
     - When MFA mode is REQUIRED. The response contains a ``setup_challenge_id`` to bootstrap MFA setup.

**URL Name:** ``rest_register``

.. note:: Disabled when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True`` (the open registration endpoint is removed in admin-managed mode).

.. note::

    **Account enumeration.** While email verification is mandatory, an address that is already in
    use gets the same ``201`` as a free one — no account is created and its owner is notified by
    email — so the endpoint cannot be used to find out who is registered. This follows allauth's
    ``ACCOUNT_PREVENT_ENUMERATION`` (enabled by default). No ``refresh`` token comes with that
    response: one cannot be issued for somebody else's address, and it is unusable until the
    address is verified anyway (authenticate through ``/login/`` once it is). Set
    ``ACCOUNT_PREVENT_ENUMERATION = False``, or disable ``EMAIL_VERIFICATION``, to reject a
    conflicting address with ``400`` and get the refresh token back.

.. note::

    **Optional verification.** With ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` the confirmation
    mail goes out but the account is usable straight away: the response carries ``access`` and a
    working ``refresh``, exactly as it does with verification off, and address conflicts are
    reported with ``400``. Gate the features that need a confirmed address on the
    ``email_verified`` claim instead — see :doc:`email_verification`.

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
   * - Cookie (HTTP-only, optional)
     - ``refresh_token``. Only when ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION = True`` (see the note below).

**URL Name:** ``account_confirm_email``

.. note:: Disabled when ``EMAIL_VERIFICATION = False``.

.. note::

    **Session on verification.** With ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION = True`` (off by
    default) the redirect carries a refresh token cookie, so the browser that follows the link lands
    on the frontend already authenticated and can call ``/refresh/`` for an access token. It applies
    to the sign-up confirmation only — confirming an address added later to an account that is
    already usable never opens a session — and regardless of whether registration hides address
    conflicts. Bear in mind that it turns the confirmation link into a credential: whoever the email
    reaches gets the session, not just a verified address.

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
   * - Header
     - ``X-CSRFToken``
     - CSRF token, from the ``csrftoken`` cookie set on the same redirect. Not required when ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF = False``.
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
   * - ``401 Unauthorized``
     - The cookie is missing, expired, already used, or the account it names has been deactivated or deleted.
   * - ``403 Forbidden``
     - Missing or invalid CSRF token.

**URL Name:** ``rest_set_password``

.. note:: Only available when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``. This endpoint is reached after the invited user clicks the verification link. The GET verification drops a one-time access token in the ``set_password_access_token`` cookie and redirects to the UI configured by ``PASSWORD_SET_REDIRECT``. Throttled with ``UserRateThrottle`` by default, in addition to the throttles configured by the project.

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
     - Access token issued when MFA mode is ``required`` and activation is performed using ``setup_challenge_id``. Omitted while the user's email address is still unverified and ``EMAIL_VERIFICATION`` is enabled.
   * - Body (JSON, optional)
     - ``refresh``
     - Refresh token issued when MFA mode is ``required`` and activation is performed using ``setup_challenge_id`` (may be delivered via HTTP-only cookie depending on settings). If the email address is still unverified and ``EMAIL_VERIFICATION`` is enabled, it is returned in the body and stays disabled until the verification link is used.

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

Failed verifications are limited per challenge and per user; once the per-user budget is spent the endpoint answers ``429`` with a ``Retry-After`` header without checking the code. See :doc:`mfa_totp`.

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

Recovery code failures share the same budgets as ``/mfa/verify/`` and answer ``429`` the same way.

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
