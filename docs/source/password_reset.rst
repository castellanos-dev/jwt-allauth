Password Reset
==============

This module provides complete functionality for the password reset process using JWT and single-use tokens.

Overview
--------

The password reset flow follows these steps:

#. User requests password reset via email.

#. System sends email with a single-user confirmation link.

#. User clicks link and receives temporary access cookie. The user is redirected to the reset password form.

#. The new password is submitted with access cookie. The user sessions are revoked by default.

#. System updates password and revokes access token.

.. rubric:: Password Reset Flow

**Step 1: Request password reset**

.. code-block:: bash

    POST /password/reset/
    {
        "email": "user@example.com"
    }

    Response (200 OK):
    {
        "detail": "Password reset e-mail has been sent."
    }

.. note::

   For security, the email is only sent if the email address exists and is verified.
   The API response is the same either way.

**Step 2: User clicks the reset link**

The user receives a link like:

.. code-block:: text

    GET /password/reset/confirm/<uidb64>/<token>/

If the link is valid, the server:

- Redirects the browser to ``PASSWORD_RESET_REDIRECT`` (or to the default UI at ``/password/reset/default/`` when ``PASSWORD_RESET_REDIRECT`` is not configured)
- Sets a one-time cookie named ``password_reset_access_token``

**Step 3: Submit the new password**

Your frontend submits the new password to the API.
The one-time token can be provided via the cookie (default) or via the Authorization header (Bearer).

.. code-block:: bash

    POST /password/reset/set-new/
    {
        "new_password1": "new_secure_password",
        "new_password2": "new_secure_password"
    }

    Response (200 OK):
    {
        "access": "...",
        "detail": "Password reset."
    }

Depending on your configuration, the refresh token is returned either:

- As an HTTP-only cookie (default, ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = True``)
- Or in the JSON response body (``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``)

Configuration
-------------

The behaviour of the password reset can be configured thanks to the following ``settings.py`` parameters:

    - ``PASSWORD_RESET_REDIRECT`` - the relative url with the form to set the new password on password reset. If not configured, the user will be redirected to the default password reset form at ``/jwt-allauth/password/reset/default/``.

    - ``PASSWORD_RESET_COOKIE_HTTP_ONLY`` - whether to set a http-only cookie (default: ``True``).

    - ``PASSWORD_RESET_COOKIE_SECURE`` - whether to set a secure cookie (default: ``not DEBUG``).

    - ``PASSWORD_RESET_COOKIE_SAME_SITE`` - same-site cookie policy (default: ``'Lax'``).

    - ``PASSWORD_RESET_COOKIE_MAX_AGE`` - maximum age of the cookie in seconds (default: ``3600``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether to revoke the existing sessions of the user (default: ``True``).
