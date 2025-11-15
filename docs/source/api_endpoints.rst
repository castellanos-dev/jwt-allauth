API endpoints
=============

Authentication
--------------

- **/login/** (POST)

    - email
    - password

  Returns: access, refresh (in cookie by default)

  Reverse name: rest_login

.. note:: Django Rest Framework throttling enabled, see: https://www.django-rest-framework.org/api-guide/throttling/

- **/refresh/** (POST)

    - refresh (from cookie by default)

  Returns: access, refresh (in cookie by default)

  Reverse name: token_refresh

- **/logout/** (POST) ``[Authenticated]``

    - refresh

  Reverse name: rest_logout

- **/logout-all/** (POST)

- **/password/reset/** (POST) ``[Authenticated]``

    - email

  Returns: access, refresh (in cookie by default)

  Reverse name: rest_password_reset

.. note:: Django Rest Framework throttling enabled, see: https://www.django-rest-framework.org/api-guide/throttling/

.. warning:: Requires a email server configured.

- **/password/reset/confirm/<str:uidb64>/<str:token>/** (GET)

  Reverse name: password_reset_confirm

.. note:: uid and token are sent in email after calling /rest-auth/password/reset/

- **/password/reset/default/** (GET)

  Reverse name: default_password_reset

.. note:: Default password reset form. Used when PASSWORD_RESET_REDIRECT is not configured.

- **/password/reset/complete/** (GET)

  Reverse name: jwt_allauth_password_reset_complete

.. note:: Used when PASSWORD_RESET_REDIRECT is not configured.

- **/password/reset/set-new/** (POST) ``[Cookie]``

    - new_password1
    - new_password2

  Reverse name: password_reset_confirm

- **/password/change/** (POST) ``[Authenticated]``

    - new_password1
    - new_password2
    - old_password

  Reverse name: rest_password_change

.. note:: ``OLD_PASSWORD_FIELD_ENABLED = True`` to use old_password (default).
.. note:: ``LOGOUT_ON_PASSWORD_CHANGE = True`` to logout from the remaining sessions.

- **/user/** (GET, PUT, PATCH) ``[Authenticated]``

    - email
    - first_name
    - last_name

  Returns: email, first_name, last_name

  Reverse name: rest_user_details

Registration
------------

- **/registration/** (POST)

    - password1
    - password2
    - email
    - first_name
    - last_name

  Reverse name: rest_register
.. note:: Disabled when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True`` (the open registration endpoint is removed in admin-managed mode).

- **/registration/user-register/** (POST) ``[Admin role]``

    - email
    - role
    - first_name (optional)
    - last_name (optional)

  Reverse name: rest_user_register

.. note:: Enabled when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``. Keeps the default ``/registration/`` endpoint unchanged unless you enable this setting. This endpoint returns 201 with an empty body and sends a verification email to the invited user.

- **/registration/verification/<str:key>/** (GET)

.. note:: Disabled when ``EMAIL_VERIFICATION = False``.

  Reverse name: account_confirm_email

- **/registration/set-password/** (POST) ``[Cookie]``

    - new_password1
    - new_password2

  Reverse name: rest_set_password

.. note:: Only available when ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``. This endpoint is reached after the invited user clicks the verification link. The GET verification drops a one-time access token in the ``set_password_access_token`` cookie and redirects to the UI configured by ``PASSWORD_SET_REDIRECT``. Throttled with ``UserRateThrottle`` by default.

- **/registration/account_email_verification_sent/** (GET)

  Reverse name: account_email_verification_sent

.. note:: Disabled when ``EMAIL_VERIFICATION = False``.

- **/registration/verified/** (GET)

  Reverse name: jwt_allauth_email_verified

.. note:: Disabled if ``EMAIL_VERIFIED_REDIRECT`` is defined or ``EMAIL_VERIFICATION = False``.

Refresh Token Configuration
---------------------------

.. note:: By default, refresh tokens are sent as secure HTTP-only cookies for enhanced security. This protects against XSS attacks by making tokens inaccessible to JavaScript. You can configure this behavior using the ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` setting. When set to ``False``, refresh tokens will be included in the JSON response payload instead.

Multi-Factor Authentication (MFA)
---------------------------------

.. note:: Requires ``allauth.mfa`` in ``INSTALLED_APPS`` of your Django project and database migrations applied.

- **/mfa/setup/** (POST) ``[Authenticated]``

  Starts TOTP setup. Returns ``provisioning_uri`` (otpauth), ``secret``, and ``qr_code`` (SVG). The client can use the QR code or secret directly.

- **/mfa/activate/** (POST) ``[Authenticated]``

    - code

  Activates TOTP after scanning the QR. Returns recovery codes.

- **/mfa/verify/** (POST)

    - challenge_id
    - code

  Completes login when MFA is enabled. Returns access (and refresh if configured in payload).

- **/mfa/verify-recovery/** (POST)

    - challenge_id
    - recovery_code

  Completes login using a one-time recovery code when MFA device is unavailable.

- **/mfa/deactivate/** (POST) ``[Authenticated]``

    - password

  Deactivates TOTP for the authenticated user.

- **/mfa/authenticators/** (GET) ``[Authenticated]``

  Lists user authenticators.

.. note:: MFA TOTP can be configured with the ``JWT_ALLAUTH_MFA_TOTP_MODE`` setting:

   - ``'disabled'`` (default): MFA endpoints return 403 Forbidden when accessed.
   - ``'optional'``: Users can set up MFA but it's not required during login.
   - ``'required'``: Users must set up MFA and provide TOTP code during login. Deactivation is blocked.
