User invitations
================

An admin creates the account; the person it belongs to receives an e-mail, follows the
link, and chooses their own password. The admin never sees or sets it, and the invited
account cannot be used until the invitee has proved control of the mailbox.

This is the flow behind staff onboarding, B2B seats and any product whose accounts are
handed out rather than opened. It ships with the library: there is no invitation model to
add, no signal to wire, and the session the invitee ends up with is an ordinary one --
on the whitelist, carrying its device, closable from ``/logout/``.

Two ways to switch it on
------------------------

.. code-block:: python

    # Invitations alongside the public sign-up: customers register themselves,
    # staff are invited.
    JWT_ALLAUTH_INVITATIONS = True

.. code-block:: python

    # Invitations only. /registration/ answers 404 and social sign-up is closed too:
    # no account exists that an admin did not create.
    JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True

The second implies the first. It is the older setting and is unchanged, so a project
already using it needs to do nothing.

Both need somewhere for the invitee to land:

.. code-block:: python

    PASSWORD_SET_REDIRECT = '/set-password/'   # your UI

Leave it unset and the library serves its own form at
``/registration/set-password/default/``.

The flow
--------

1. **The admin creates the account** — ``POST /registration/user-register/``, authorized
   by role (see `Who may invite`_):

   .. code-block:: json

      {"email": "writer@demo.com", "role": 300, "first_name": "Optional", "last_name": "Optional"}

   Answers ``201`` with an empty body. No token is issued: the account has no password
   and nobody has proved the address yet.

2. **The invitee receives the e-mail** and follows the link —
   ``GET /registration/verification/<key>/``. The address is confirmed, a one-time
   capability is dropped in the ``set_password_access_token`` cookie, and the browser is
   redirected to ``PASSWORD_SET_REDIRECT``.

3. **The invitee chooses a password** — ``POST /registration/set-password/`` with
   ``new_password1``/``new_password2``. Answers with the access token and the refresh
   token cookie: the invitation is complete and they are signed in.

Who may invite
--------------

``RegisterUsersPermission`` reads the caller's ``role`` claim, so the check costs no
database query. ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES`` defaults to
``[STAFF_CODE, SUPER_USER_CODE]`` and takes any list of role codes, which is how a
project grants "can invite" to a role of its own without granting staff access to the
Django admin.

How an invitation is told apart from a sign-up
-----------------------------------------------

Both arrive through the same confirmation link, and with ``JWT_ALLAUTH_INVITATIONS`` both
can be in flight at once. What separates them is the password: an invited account has
none until it claims one, and a self-service sign-up chose one to register.

So the password-set capability is issued only to an account that has no password. One
that already has a password is still confirmed by its link -- that is what the link was
sent for -- but gets no capability, because issuing one would turn every confirmation
link into a password reset that bypasses the reset flow and its throttling.

What the link is worth
----------------------

- It stays usable until the password is set, so an e-mail scanner opening it first does
  not burn the invitation. Each access supersedes the capability the previous one issued.
- It expires with ``ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS`` (3 days by default),
  whatever it has or has not been used for.
- Only the SHA-256 digest of the key is stored, so the link cannot be reconstructed from
  a database dump.
- The capability is claimed atomically: two set-password requests carrying the same
  cookie cannot both succeed.
- A deactivated account is never handed one, and a capability issued before a
  deactivation is refused with ``401``.
- The set-password request must carry a CSRF token, since the capability travels in a
  cookie. The verification ``GET`` sets the CSRF cookie alongside it and the built-in
  form sends it back; set ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF = False`` to skip the check.

Duplicate addresses
-------------------

An address held by a **verified** account is refused with ``400``. One held only by an
account that was never confirmed and never used is taken over, and that account is
removed: nobody had proved it was theirs. It is the same rule self-service registration
applies, in :func:`jwt_allauth.accounts.superseded_accounts`.

With a second factor required
-----------------------------

Under ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'`` the invitation does not end at the
password. ``POST /registration/set-password/`` answers with an enrolment challenge
instead of a session:

.. code-block:: json

    {
        "mfa_setup_required": true,
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
        "detail": "Password set. Please configure MFA to complete registration."
    }

The invitee enrols through ``POST /mfa/setup/`` and ``POST /mfa/activate/`` carrying that
``setup_challenge_id``, and **the session is issued as soon as the authenticator is
active** -- no second sign-in. Self-service registration behaves differently there:
``/mfa/activate/`` returns only the recovery codes and the user signs in afterwards. The
difference is deliberate. An invitee has just proved the mailbox and chosen a password in
the same sitting; sending them to a login form would be asking them to prove it twice.

Templates
---------

The invitation e-mail has templates of its own, so it can say "you have been invited"
rather than "confirm your address":

- Subject — ``email/admin_invite/email_subject.txt``
- Body — ``email/admin_invite/email_message.html``
- Invalid or expired link — ``registration/verification_failed.html``

Override them through ``JWT_ALLAUTH_TEMPLATES`` with the keys
``ADMIN_EMAIL_VERIFICATION_SUBJECT``, ``ADMIN_EMAIL_VERIFICATION`` and
``EMAIL_VERIFICATION_FAILED_TEMPLATE``. See :doc:`configuration.settings_py`.

Settings
--------

- ``JWT_ALLAUTH_INVITATIONS`` (default: ``False``) — serve the invitation endpoints,
  leaving self-service registration as it is.
- ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` (default: ``False``) — invitations *and* no
  self-service registration. Implies the above.
- ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES`` (default: ``[STAFF_CODE, SUPER_USER_CODE]``)
- ``PASSWORD_SET_REDIRECT`` — the UI the confirmation link redirects to.
- ``PASSWORD_SET_COOKIE_HTTP_ONLY`` (default: ``True``),
  ``PASSWORD_SET_COOKIE_SECURE`` (default: ``not DEBUG``),
  ``PASSWORD_SET_COOKIE_SAME_SITE`` (default: ``'Lax'``),
  ``PASSWORD_SET_COOKIE_MAX_AGE`` (default: ``86400``)

See also
--------

- :doc:`api_endpoints` — request and response of each endpoint.
- :doc:`mfa_totp` — the MFA flows in full.
- :doc:`configuration.settings_py` — every setting named here.
