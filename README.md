JWT Allauth
===========

**Device-level session management for Django REST Framework, with refresh token theft detection.**

JWT Allauth gives every login its own tracked session, rotates the refresh token on each
use, and — when a rotated token is presented a second time — revokes the entire session
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
already been rotated. Simple JWT's blacklist rejects that second request and stops there
— so if the attacker refreshes first, the *user* gets locked out while the *attacker*
keeps a valid, indefinitely renewable session. The theft never surfaces.

A replay is evidence that a session is compromised, and it is treated as such here: the
whole session is revoked and both parties have to log in again. This is the behaviour
described in [OAuth 2.0 Security Best Current Practice §4.14.2](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics#section-4.14.2),
and it is the reason this library exists.


How it compares
---------------

|                                                       | Simple JWT | dj-rest-auth | allauth headless | **JWT Allauth** |
|-------------------------------------------------------|:----------:|:------------:|:----------------:|:---------------:|
| JWT access/refresh tokens out of the box               |     ✓      |      ✓       |      ✗ &nbsp;¹    |        ✓        |
| Refresh token rotation                                 |     ✓      |      ✓       |        —         |        ✓        |
| **Replay revokes the whole session**                   |     ✗      |      ✗       |        —         |      **✓**      |
| **Session records per device** (IP, OS, browser)       |     ✗      |      ✗       |     ✗ &nbsp;²     |      **✓**      |
| **Absolute session lifetime across rotations**         |     ✗      |      ✗       |        —         |      **✓**      |
| **Role and claims re-read from the DB on rotation**    |     ✗      |      ✗       |        —         |      **✓**      |
| Login, sign-up, e-mail verification, password reset    |     ✗      |      ✓       |        ✓         |        ✓        |
| MFA (TOTP + recovery codes)                            |     ✗      |      ✗       |        ✓         |        ✓        |
| **Social authentication**                              |     —      |    **✓**     |      **✓**       |    **not yet**  |

¹ `allauth.headless` exposes `AbstractTokenStrategy`: *"We make no assumptions in this regard.
If you need access tokens, you will have to implement a token strategy that returns an access
token here."* The rows marked — follow from that: there is no token implementation to compare.

² `allauth.usersessions` lists Django sessions, not JWT sessions.

**If you need social authentication today, use dj-rest-auth or allauth headless.** It is
the one thing this library does not do, and no amount of session handling makes up for it.


Quick Start
-----------

Install using `pip`:

    pip install django-jwt-allauth

You can start a new Django project with JWT Allauth pre-configured:

    jwt-allauth startproject myproject

Then:

    cd myproject
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver

Available options:
- `--email=True` — enables email configuration in the project
- `--template=PATH` — uses a custom template directory for project creation


Adding it to an existing project
--------------------------------

No particular user model is required. Roles are read from a `role` field when the user
model has one, and derived from `is_staff` / `is_superuser` when it does not — so a
project that cannot swap `AUTH_USER_MODEL` (which is most of them past the first
migration) still gets staff and superusers told apart from regular users, with nothing to
migrate.

To define roles of your own, add the field to the user model you already have:

```python
from django.contrib.auth.models import AbstractUser
from jwt_allauth.models import RoleMixin

class MyUser(RoleMixin, AbstractUser):
    pass
```

Existing staff rows need backfilling in that migration, or they drop to a regular user on
their next login — see the [user model documentation](https://jwt-allauth.readthedocs.io/en/latest/configuration.user_model.html).
New projects can skip all of it with `AUTH_USER_MODEL = 'jwt_allauth.JAUser'`.


Features
--------

- **Refresh token whitelist**: every login gets a session row carrying the device it was
  issued to — IP, browser, OS, device model — so sessions can be listed and revoked
  individually, or all at once.
- **Replay detection**: a rotated refresh token presented twice revokes the session it
  belongs to, on the assumption that two parties are holding it.
- **Absolute session lifetime**: rotation cannot extend a session past
  `JWT_ALLAUTH_SESSION_LIFETIME`; the `exp` of both tokens is capped to it.
- **Claims that stay current**: role, e-mail verification state and custom claims are
  re-read from the database on every rotation, so a privilege change applies within the
  lifetime of one access token instead of surviving until the refresh token expires.
- **Stateless by default**: access tokens are verified without a database query.
  `JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK` trades one indexed query per request for
  immediate revocation of access tokens too.
- **Revocation on credential change**: setting a password drops every session, every
  outstanding capability (unused reset links, MFA challenges) and every unconfirmed
  secondary address.
- **Role-based permissions**: authorization from a JWT claim, with no user table lookup.
- **The rest of the flows**: e-mail verification, password reset and change, MFA over
  TOTP with recovery codes, admin-managed registration, session logout.
- **Effortless setup**: get a project running with a single command.


Why whitelisting?
-----------------

The refresh token whitelist tracks the devices **authorized by the user**, stored in the
database and checked when a refresh token is exchanged for a new access token.

This is what lets users **revoke access** to a stolen or lost device, or sign out of every
session at once. Refresh tokens are regenerated on each use, so the whitelist is an
accurate picture of which sessions are live — and it is what makes replay detection
possible at all: a token that is not in the whitelist has either been rotated already or
was forged, and both answers mean the session goes down.

Auto-renewal keeps sessions alive without repeated logins — ideal for **mobile apps**,
where users should not have to reauthenticate every time they open the app.

Access tokens stay short-lived and self-contained, so ordinary API requests are
authenticated **without touching the database**.


Email verification
------------------

To enable email verification, configure the email provider in your `settings.py`:

    EMAIL_VERIFICATION = True
    EMAIL_HOST = ...
    EMAIL_PORT = ...
    EMAIL_HOST_USER = ...
    EMAIL_HOST_PASSWORD = ...
    EMAIL_USE_TLS = ...
    DEFAULT_FROM_EMAIL = ...

`EMAIL_VERIFICATION` also accepts `'mandatory'`, `'optional'` and `'none'` by name.


Redirection URLs
----------------

The relative url to be redirected once the email is verified:

    EMAIL_VERIFIED_REDIRECT = ...

The relative url with the form to set the new password on password reset:

    PASSWORD_RESET_REDIRECT = ...

If not configured, users will be redirected to the default password reset form at
`/jwt-allauth/password/reset/default/`. This form provides a modern, responsive interface
for password reset with proper form validation and error handling.


Templates
---------

The templates can be configured in a `JWT_ALLAUTH_TEMPLATES` dictionary:

- `PASS_RESET_SUBJECT` — subject of the password reset email (default: `email/password/reset_email_subject.txt`).
- `PASS_RESET_EMAIL` — template of the password reset email (default: `email/password/reset_email_message.html`).
- `EMAIL_VERIFICATION_SUBJECT` — subject of the signup email verification sent (default: `email/signup/email_subject.txt`).
- `EMAIL_VERIFICATION` — template of the signup email verification sent (default: `email/signup/email_message.html`).

Example:

    JWT_ALLAUTH_TEMPLATES = {
        'PASS_RESET_SUBJECT': 'mysite/templates/password_reset_subject.txt',
        ...
    }


Documentation
-------------

Full documentation at [jwt-allauth.readthedocs.io](https://jwt-allauth.readthedocs.io/).


Acknowledgements
----------------
This project began as a fork of django-rest-auth. Thanks to the authors for their great work.
