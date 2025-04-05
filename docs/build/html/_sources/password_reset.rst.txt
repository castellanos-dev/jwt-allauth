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

Configuration
-------------

The behaviour of the password reset can be configured thanks to the following ``settings.py`` parameters:

    - ``PASSWORD_RESET_REDIRECT`` - the relative url with the form to set the new password on password reset. If not configured, the user will be redirected to the default password reset form at ``/jwt-allauth/password/reset/default/``.

    - ``PASSWORD_RESET_COOKIE_HTTP_ONLY`` - whether to set a http-only cookie (default: ``True``).

    - ``PASSWORD_RESET_COOKIE_SECURE`` - whether to set a secure cookie (default: ``not DEBUG``).

    - ``PASSWORD_RESET_COOKIE_SAME_SITE`` - same-site cookie policy (default: ``'Lax'``).

    - ``PASSWORD_RESET_COOKIE_MAX_AGE`` - maximum age of the cookie in seconds (default: ``3600``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether to revoke the existing sessions of the user (default: ``True``).
