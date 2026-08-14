Security Policy
===============

Supported versions
------------------

Fixes are released against the latest published version. There are no long-term support
branches: if you are behind, the upgrade path is forward.

| Version | Supported |
|---------|-----------|
| 1.4.x   | ✅        |
| < 1.4   | ❌        |


Reporting a vulnerability
-------------------------

**Do not open a public issue for a security problem.**

Report it privately through GitHub's
[security advisory form](https://github.com/castellanos-dev/jwt-allauth/security/advisories/new),
which is the preferred channel. If that is not available to you, email
**fcastellanos.dev@gmail.com** with `jwt-allauth security` in the subject.

What helps, in rough order of usefulness:

- The version of `django-jwt-allauth`, Django, `django-allauth` and Simple JWT.
- The settings that matter to the report — `EMAIL_VERIFICATION`,
  `JWT_ALLAUTH_MFA_TOTP_MODE`, `JWT_ALLAUTH_SESSION_LIFETIME`,
  `JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`, `JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`.
- A sequence of requests that reproduces it, or a failing test.
- What an attacker gets out of it, and what they need to hold before they start.

This is a one-maintainer project, so please do not expect same-day acknowledgement.
Expect a first reply within a week. If a report is confirmed, you will be told what the
fix is and when it ships, and credited in the release notes unless you would rather not
be.


Scope
-----

In scope — anything that lets a request do something the session behind it should not be
able to do:

- Authenticating as another account, or keeping access to one after it should have ended:
  a revoked session that still rotates, a password change or reset that leaves a session
  alive, a deactivated account that can still refresh.
- A refresh token accepted after it has been rotated, or a replay that does not take its
  session down with it.
- Privilege claims — `role`, `email_verified` — that can be made to say something the
  database does not.
- MFA that can be skipped, or the lockout counters cleared by an unauthenticated caller.
- Password reset, e-mail confirmation and MFA capability tokens being reusable,
  guessable, or usable against an account other than the one they were issued for.
- Account enumeration through response differences or timing on the public endpoints.

Out of scope:

- Findings that need settings the documentation warns against, such as
  `JWT_ALLAUTH_SECRET_KEY` left on Django's `SECRET_KEY` in production.
- The consequences of a leaked signing key. Every JWT issued is forgeable; that is what
  the key is.
- Access tokens outliving a revoked session. This is documented, bounded by
  `JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME`, and closed by
  `JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK` — see
  [Refresh token rotation is not enough](https://jwt-allauth.readthedocs.io/en/latest/refresh_token_theft.html).
  A concrete way to widen that window past the access token lifetime is in scope.
- Vulnerabilities in Django, django-allauth or Simple JWT themselves. Report those
  upstream; if this library's use of them makes an upstream issue exploitable where it
  otherwise would not be, that is in scope here.
- Denial of service through ordinary request volume. The endpoint throttles are a rate
  limit, not a DoS defence.
