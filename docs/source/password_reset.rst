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

Both the confirmation link and the access cookie it grants are claimed atomically, so each of them is honoured
exactly once even when two requests arrive at the same time. Requesting a new reset also supersedes the cookie
granted by the previous one: only the most recent link can set a password.

The account is re-read when the cookie is used: a link issued before the account was deactivated or deleted is
rejected with ``401``, and a deactivated account is never handed a cookie in the first place.

None of the three endpoints of the flow authenticates the caller: authorization is the cookie, so an
``Authorization`` header travelling with the request is ignored rather than rejected. Clients that attach a
bearer token to everything they send can complete a reset, and a stale one does not turn the link into a
``401``.

Rate limiting
-------------

Requesting a reset is limited twice: by DRF's ``anon`` throttle, which counts per address of origin, and by
allauth's ``reset_password`` limit keyed by the target address (``5/m/key`` next to its own ``20/m/ip``). The
second is what protects the mailbox: without it, rotating the origin is enough to bury somebody's inbox in
reset links. It is consumed before the account is looked up, so an unregistered address answers exactly like a
registered one — ``429`` in both cases. Tune it, or lift it, through allauth's ``ACCOUNT_RATE_LIMITS``:

.. code-block:: python

    ACCOUNT_RATE_LIMITS = {'reset_password': '3/m/key,20/m/ip'}   # or None to lift it

CSRF
----

The access cookie authenticates the request that sets the new password, so that request has to carry a CSRF
token as well — a cookie alone travels from any origin the ``SameSite`` policy allows. The redirect that hands
out the access cookie sets the CSRF cookie too, and the form is expected to send its value back in the
``X-CSRFToken`` header; the built-in form already does. Set ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF = False`` to
skip the check.

Configuration
-------------

The behaviour of the password reset can be configured thanks to the following ``settings.py`` parameters:

    - ``PASSWORD_RESET_REDIRECT`` - the relative url with the form to set the new password on password reset. If not configured, the user will be redirected to the default password reset form at ``/jwt-allauth/password/reset/default/``.

    - ``PASSWORD_RESET_COOKIE_HTTP_ONLY`` - whether to set a http-only cookie (default: ``True``).

    - ``PASSWORD_RESET_COOKIE_SECURE`` - whether to set a secure cookie (default: ``not DEBUG``).

    - ``PASSWORD_RESET_COOKIE_SAME_SITE`` - same-site cookie policy (default: ``'Lax'``).

    - ``PASSWORD_RESET_COOKIE_MAX_AGE`` - maximum age of the cookie in seconds (default: ``3600``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether to revoke the existing sessions of the user (default: ``True``).
