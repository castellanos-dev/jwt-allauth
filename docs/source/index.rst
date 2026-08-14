.. JWT Allauth documentation master file, created by
   sphinx-quickstart on Mon Mar 10 20:15:01 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

JWT Allauth
===========

**Device-level session management for Django REST Framework, with refresh token theft
detection.**

JWT Allauth gives every login its own tracked session, rotates the refresh token on each
use, and -- when a rotated token is presented a second time -- revokes the entire session
rather than just rejecting the replayed credential. Around that it ships the endpoints an
API needs to be usable on day one: login, sign-up, e-mail verification, password reset,
MFA and role-based permissions.

Built on Django REST Framework, django-allauth and Simple JWT.


The problem it solves
---------------------

Rotating refresh tokens is standard advice, and every Django stack does it. What almost
none of them do is handle the case rotation exists for.

When a refresh token is stolen, both the attacker and the legitimate user hold a
credential from the same session. Whoever refreshes second presents a token that has
already been rotated. A blacklist rejects that second request and stops there -- so if the
attacker refreshes first, the *user* gets locked out while the *attacker* keeps a valid,
indefinitely renewable session. The theft never surfaces.

A replay is evidence that a session is compromised, and it is treated as such here: the
whole session is revoked and both parties have to log in again. This is the behaviour
described in `OAuth 2.0 Security Best Current Practice §4.14.2
<https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics#section-4.14.2>`_,
and it is the reason this library exists.

.. note::

    Social authentication is the one thing JWT Allauth does not do. If a project needs it
    today, `dj-rest-auth <https://github.com/iMerica/dj-rest-auth>`_ and
    `allauth.headless <https://docs.allauth.org/en/latest/headless/index.html>`_ cover it.


Relationship to Simple JWT
--------------------------

Simple JWT is not an alternative to this package -- it is the layer underneath it, and a
hard dependency. Tokens are its ``RefreshToken`` subclassed, requests are authenticated by
its ``JWTAuthentication`` subclassed, and signing, claims and verification are its code,
untouched.

What JWT Allauth replaces is the part of Simple JWT that decides when a session ends.

Simple JWT rotates refresh tokens and, through its optional ``token_blacklist`` app,
rejects one that has already been rotated. JWT Allauth refuses that arrangement outright
-- ``BLACKLIST_AFTER_ROTATION = True`` raises at startup, and rotation is compulsory --
and keeps a **whitelist keyed by session** in its place. A refresh token that is not on
the whitelist is not merely rejected: the session it names is revoked, because a rotated
token turning up again means two parties are holding it.

That inversion, deny-list to allow-list, is what the rest of this package hangs off. The
device records, the absolute session lifetime and the claims re-read on rotation are all
things that become possible once a session is a row you own rather than the absence of
one.

So the question is never *Simple JWT or this?* -- it is *Simple JWT on its own, or Simple
JWT with a session model over it?* A project that only needs signed tokens should use
Simple JWT directly and stop there.


Features
--------

- **Refresh token whitelist**: in place of Simple JWT's blacklist, every login gets a session row carrying the device it was issued to -- IP, browser, OS, device model -- so sessions can be listed and revoked individually, or all at once.
- **Replay detection**: a rotated refresh token presented twice revokes the session it belongs to, on the assumption that two parties are holding it.
- **Absolute session lifetime**: rotation cannot extend a session past ``JWT_ALLAUTH_SESSION_LIFETIME``; the ``exp`` of both tokens is capped to it.
- **Claims that stay current**: role, e-mail verification state and custom claims are re-read from the database on every rotation, so a privilege change applies within the lifetime of one access token instead of surviving until the refresh token expires.
- **Stateless by default**: access tokens are verified without a database query. ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`` trades one indexed query per request for immediate revocation of access tokens too.
- **Revocation on credential change**: setting a password drops every session, every outstanding capability (unused reset links, MFA challenges) and every unconfirmed secondary address.
- **Role-based permissions**: authorization from a JWT claim, with no user table lookup, on any user model.
- **Refresh tokens as HttpOnly cookies** by default, keeping the longest-lived credential out of reach of JavaScript.
- **The rest of the flows**: e-mail verification, password reset and change, MFA over TOTP with recovery codes, admin-managed registration, session logout.
- **Effortless setup**: get a project running with a single command.


Why whitelisting?
-----------------

The refresh token whitelist tracks the devices **authorized by the user**, stored in the
database and checked when a refresh token is exchanged for a new access token.

This is what lets users **revoke access** to a stolen or lost device, or sign out of every
session at once. Refresh tokens are regenerated on each use, so the whitelist is an
accurate picture of which sessions are live -- and it is what makes replay detection
possible at all: a token that is not in the whitelist has either been rotated already or
was forged, and both answers mean the session goes down.

Auto-renewal keeps sessions alive without repeated logins -- ideal for **mobile apps**,
where users should not have to reauthenticate every time they open the app.

Access tokens stay short-lived and self-contained, so ordinary API requests are
authenticated **without touching the database**.


Quick Start
-----------

Install using ``pip``...

.. code-block:: bash

    pip install django-jwt-allauth

You can quickly start a new Django project with JWT Allauth pre-configured using the ``startproject`` command:

.. code-block:: bash

    jwt-allauth startproject myproject

This will create a new Django project called "myproject" with JWT Allauth pre-configured. Then:

.. code-block:: bash

    cd myproject
    python manage.py makemigrations jwt_allauth
    python manage.py migrate
    python manage.py runserver

Available options:

- ``--email=True`` - Enables email configuration in the project
- ``--template=PATH`` - Uses a custom template directory for project creation


Adding it to an existing project
--------------------------------

No particular user model is required. Roles are read from a ``role`` field when the user
model has one, and derived from ``is_staff`` / ``is_superuser`` when it does not -- so a
project that cannot swap ``AUTH_USER_MODEL`` (which is most of them past the first
migration) still gets staff and superusers told apart from regular users, with nothing to
migrate.

To define roles of its own, a project adds the field to the user model it already has:

.. code-block:: python

    from django.contrib.auth.models import AbstractUser
    from jwt_allauth.models import RoleMixin

    class MyUser(RoleMixin, AbstractUser):
        pass

See :doc:`configuration.user_model` for the three configurations, and for the backfill
existing staff rows need.


Source Code
-----------

The source code is available at `GitHub <https://github.com/castellanos-dev/jwt-allauth>`_.


Contents
--------
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
   release_notes

Acknowledgements
----------------
This project began as a fork of django-rest-auth. Thanks to the authors for their great work.
