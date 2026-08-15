Social Login
============

JWT Allauth signs users in through an identity provider -- Google, Apple, and anything
else ``django-allauth`` registers -- and hands back the same session every other endpoint
hands back: an access token in the body, a rotating refresh token in an HttpOnly cookie,
and a row on the whitelist that ``/logout/`` can close.

One view serves every provider. The provider id travels in the URL and is resolved
through allauth's registry, so adding one is a matter of configuration; there is no view
to subclass and no adapter to name.

Prerequisites
-------------

Install this package's ``social`` extra, which is the only command needed -- it brings the
whole dependency chain with it:

.. code-block:: bash

    pip install "django-jwt-allauth[social]"

What arrives with it is the HTTP stack the flows need: ``requests``, the OAuth2 client and
``pyjwt[crypto]``. That last one is not a second JWT library -- Simple JWT already depends
on PyJWT. What it adds is ``cryptography``, which PyJWT needs for the RS256/ES256 signature
an ``id_token`` carries; Simple JWT signs this library's own tokens with HS256 and never
needed it.

Add ``allauth.socialaccount`` to ``INSTALLED_APPS``, along with the provider's app:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'jwt_allauth',
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'allauth.socialaccount.providers.google',
    ]

Then run migrations -- the provider connections are allauth's models:

.. code-block:: bash

    python manage.py migrate

The endpoints are routed only when both halves are present: ``allauth.socialaccount`` in
``INSTALLED_APPS`` and the ``social`` extra installed. With a provider configured and the
extra missing they stay absent rather than failing on the first request, and
:ref:`jwt_allauth.W004 <social-checks>` says which half is missing at startup.

Configuration
-------------

Credentials can live in ``settings.py`` rather than in the database:

.. code-block:: python

    SOCIALACCOUNT_PROVIDERS = {
        'google': {
            'APPS': [{
                'client_id': os.environ['GOOGLE_CLIENT_ID'],
                'secret': os.environ['GOOGLE_CLIENT_SECRET'],
            }],
            'SCOPE': ['profile', 'email'],
        },
    }

Registering the app through the Django admin works too, and is what
``django.contrib.sites`` is for. Settings-based apps need neither.

The flows
---------

Two ways in, depending on what the client can do.

Provider token
~~~~~~~~~~~~~~

For a client that talks to the provider itself -- a mobile SDK, Google's JavaScript
library -- and ends up holding an ``id_token`` or an ``access_token``.

.. code-block:: http

    POST /jwt-allauth/social/google/token/ HTTP/1.1

    {
      "id_token": "eyJhbGciOi...",
      "client_id": "1234-abc.apps.googleusercontent.com"
    }

``client_id`` is required. It names the OAuth client the credential was issued for, so
that the provider can check the credential against it -- Google's verification validates
the ``aud`` claim against exactly this value. Without it the endpoint would have to guess
which configured app to verify against, and would happily verify a credential against a
client it was never issued for.

Not every provider can verify a token out of band. One that cannot answers ``400``
``flow_not_supported``; use the code flow instead.

Authorization code
~~~~~~~~~~~~~~~~~~

For a browser client. The code is exchanged with the provider server side, so the app
secret never reaches the frontend.

.. code-block:: http

    POST /jwt-allauth/social/google/code/ HTTP/1.1

    {
      "code": "4/0Ade...",
      "callback_url": "https://app.example.com/auth/callback",
      "code_verifier": "dBjftJeZ4CVP..."
    }

``callback_url`` has to match the ``redirect_uri`` of the authorization request byte for
byte, or the provider refuses the exchange. ``code_verifier`` is the PKCE verifier and is
passed straight through; send it whenever the authorization request carried a challenge.

The response
~~~~~~~~~~~~

Both answer ``200`` with either a session:

.. code-block:: json

    {"access": "eyJ0eXAiOi..."}

or, when the account has a second factor, the same MFA challenge ``/login/`` returns:

.. code-block:: json

    {"mfa_required": true, "challenge_id": "..."}

A provider proves the first factor, not the second. If a social login skipped TOTP, TOTP
would be bypassable by anyone who compromised the identity provider account -- which is
part of the population it exists to protect against. Complete the challenge at
``/jwt-allauth/mfa/verify/`` exactly as you would after a password login.

When the address already belongs to somebody
--------------------------------------------

This is the decision worth understanding, because it is where this library and allauth
part ways.

An account here is identified by its e-mail address. So when a provider vouches for
``ana@example.com`` and a local account already holds it, the question is whether they
are the same person. JWT Allauth answers it with the rule registration already uses --
:func:`jwt_allauth.accounts.superseded_accounts` -- and treats the two answers
differently:

**The address is claimed.** It has been confirmed, or the account has been used, or it is
a staff account. Somebody established ownership of it, the provider has just proved
control of the same mailbox, and they are the same person. The provider is connected and
**the password is left alone**: from then on either one signs the account in. This is
what makes "I registered with a password in March and clicked *Sign in with Google* in
November" work, and keep working.

**The address is unclaimed.** Never confirmed, on an account that was never used. Anybody
could have typed it into a sign-up form, including somebody who does not own it. Those
accounts are superseded -- removed whole -- exactly as a duplicate registration
supersedes them, and the provider account is created fresh.

allauth's own path, ``SOCIALACCOUNT_EMAIL_AUTHENTICATION``, does not draw that line: it
wipes the local password whenever it matches an account by address. That is the safe
answer if you cannot tell the two cases apart, and it is why setting allauth's flag has
no effect on these endpoints: the match it would make by address is discarded, so this
module's rule is the one that decides. Use ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING`` instead;
:ref:`jwt_allauth.W005 <social-checks>` points it out at startup if you set allauth's.

.. warning::

    The trust boundary is the provider. Linking rests entirely on the provider's claim
    that it has verified the address, so a provider that asserts ``email_verified`` for a
    mailbox it never checked can sign in to any account holding that address. Configure
    providers you trust, and use the list form of the setting to say which ones:

    .. code-block:: python

        # Trust Google's word; make everyone else earn a connection the explicit way.
        JWT_ALLAUTH_SOCIAL_EMAIL_LINKING = ['google']

With linking off for a provider, an address that belongs to somebody answers ``409``
``email_already_registered``. The way through is then the explicit one: sign in with the
password, and call the connect endpoint from that session.

An address nobody vouched for
-----------------------------

If the provider supplies no verified address, the login answers ``400``
``provider_email_unverified`` and nothing is created. An account whose address has not
been proved is a dead end here: there is no password to reset it with, and no
confirmation link worth sending to an address the provider itself would not stand behind.

Setting ``JWT_ALLAUTH_SOCIAL_REQUIRE_VERIFIED_EMAIL = False`` lets the account be created
anyway. It only makes sense under ``EMAIL_VERIFICATION = 'optional'`` or ``'none'``: with
verification mandatory the account is refused a session right afterwards and the whole
sign-up rolls back, and no confirmation mail is sent — these flows never call allauth's
``perform_login``, which is what sends one.

Connecting and disconnecting
----------------------------

.. code-block:: http

    POST /jwt-allauth/social/google/connect/token/ HTTP/1.1
    Authorization: Bearer <access token>

    {"id_token": "eyJhbGciOi...", "client_id": "1234-abc.apps.googleusercontent.com"}

Connecting is account management, not authentication: no session is opened, and none of
the caller's existing sessions are disturbed. The provider's addresses are not added to
the account either, so a provider cannot graft an address onto an account that did not
choose it. A provider account already connected to somebody else answers ``409``; the row
is never re-pointed.

``GET /jwt-allauth/social/accounts/`` lists the caller's connections, and
``DELETE /jwt-allauth/social/accounts/<id>/`` removes one. Removing the last connection
of an account with no usable password is refused with ``400``
``disconnect_not_allowed``: an account created through a provider has no password to fall
back to, so that request would lock its owner out for good.

``GET /jwt-allauth/social/providers/`` lists what is configured, with the ``client_id``
each authorization request needs. The app secret is never part of it.

.. _social-checks:

Startup checks
--------------

- ``jwt_allauth.W004`` -- a provider is configured but the installation cannot serve it:
  either the ``social`` extra is missing, so the endpoints are not routed, or no provider
  app carries credentials, so every one of them answers ``404``. Silent until the project
  asks for a provider -- having ``allauth.socialaccount`` installed is not asking, since
  ``jwt-allauth startproject`` writes it into every generated project.
- ``jwt_allauth.W005`` -- ``SOCIALACCOUNT_EMAIL_AUTHENTICATION`` is declared, globally or
  per provider, and these endpoints override it. See above.

What is not covered
-------------------

- **No server-initiated redirect endpoint.** Both flows are driven by the client: it
  makes the authorization request, holds the ``state`` and the PKCE verifier, and posts
  what comes back. There is nothing for the server to remember, which is also why this
  feature adds no model and no migration.
- **No OAuth1 providers.** The modern surface this is built on -- token verification and
  the OAuth2 adapter -- does not cover them.
- **Provider tokens are not stored** on repeat logins beyond what
  ``SOCIALACCOUNT_STORE_TOKENS`` does at sign-up.
