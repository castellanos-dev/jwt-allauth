Release Notes
=============

Version 1.2.5
-------------

Released: August 11, 2026

Security
~~~~~~~~

- **Privileges are re-read from the database on refresh token rotation**: the ``role`` claim (and any claim configured through ``JWT_ALLAUTH_USER_ATTRIBUTES``) used to be copied verbatim from the old refresh token into the rotated one, so a privilege change only took effect once the refresh token expired — a demoted administrator kept its administrator claim indefinitely as long as it kept refreshing. The refresh endpoint now loads the user behind the whitelisted token and regenerates those claims from the database, so a role change applies on the next rotation.

- **Email confirmation links no longer act as unbounded password reset links**: in admin-managed registration, the confirmation link is exchanged for a one-time permission to set a password. That permission was granted even when the link had expired — allauth's expiry rejection was swallowed as long as the account owned any verified email address — and regardless of whether the account already had a password, so an old confirmation email (for instance one sent when adding a secondary address) could be replayed at any time to take over an established account. The confirmation is now rejected past ``ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS``, is never exchanged for a password set permission when the account already has a usable password, and each access supersedes the permission issued by the previous one. Multi-use until the password is set is preserved within the expiration window.

- **Email confirmation keys hashed at rest**: in admin-managed registration the confirmation key was stored verbatim in ``GenericTokenModel``, so read access to the database exposed a usable link for every pending invitation. Only its SHA-256 digest is persisted now, matching how the other single-use tokens are already stored. This change is backward compatible — confirmations issued by a prior version remain in plain text and keep working until they expire.

- **Email verification is no longer bypassable through the MFA bootstrap**: when ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'``, ``POST /registration/`` answers an anonymous caller with a ``setup_challenge_id`` before the address is confirmed, and ``/mfa/activate/`` exchanged that challenge for a fully enabled session — so anyone could register an address they do not own, complete the TOTP setup with their own authenticator, and obtain a working session on the account despite ``EMAIL_VERIFICATION = True``. The bootstrap now checks the account's verification state: while the address is unverified no access token is issued and the refresh token is created disabled, matching registration without MFA. The login and set-password bootstraps already require a verified address and keep issuing a full session.

- **TOTP brute force limited per user, not just per challenge**: a login challenge was invalidated after 5 failed codes, but the budget was scoped to the challenge, so an attacker holding the password could log in again for a fresh one and keep guessing. Failed verifications are now also counted per user, across every challenge and both verification endpoints (``JWT_ALLAUTH_MFA_MAX_ATTEMPTS``, default 10, over a sliding ``JWT_ALLAUTH_MFA_LOCKOUT_SECONDS`` window, default 900): once the budget is spent, outstanding challenges are dropped, ``/mfa/verify/`` and ``/mfa/verify-recovery/`` answer ``429`` with ``Retry-After`` without checking the code, and ``/login/`` refuses to issue a new challenge. The bookkeeping also counted attempts right after writing them without a lock, letting concurrent requests slip under the threshold; it now runs in a transaction that locks the user row first.

- **Refresh rejected for deactivated accounts**: rotating a refresh token now requires the account to be active. When ``is_active`` is ``False`` the refresh is rejected and the user's whitelisted refresh tokens are removed, which ends every session of the account. Previously only ``LoginView`` checked ``is_active``, so a deactivated user kept its sessions alive by refreshing.

New Features
~~~~~~~~~~~~

- **Optional session revocation check on access tokens**: revoking a session removes its refresh tokens from the whitelist, which stops rotation, but the access tokens already issued for it keep working until they expire (up to ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME``). Setting the new ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK = True`` (default ``False``) makes authentication check the ``session`` claim against the whitelist on every request, so ``/logout/``, a reused refresh token or any other revocation takes effect immediately, at the cost of one indexed query per request. ``jwt_allauth.authentication.JWTAllAuthAuthentication`` is now the default authentication class and applies it; ``SessionRevocationMixin`` is available for projects with their own class. The whitelist ``jti`` and ``session`` columns are also indexed now: run ``python manage.py makemigrations jwt_allauth && python manage.py migrate``.

- **Optional absolute session lifetime**: sessions remain sliding by default — they stay alive for as long as they are used and expire after ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME`` of inactivity — but the new ``JWT_ALLAUTH_SESSION_LIFETIME`` setting (default ``None``, no limit) caps how long a session may live in total, no matter how often it is refreshed. Refresh tokens now carry a ``session_iat`` claim, set when the session starts and preserved across rotations, so the limit is measured from the login instead of the last rotation. When it is reached the refresh endpoint revokes the whole session and answers ``401`` with code ``session_expired``; until then no token is issued with an expiration beyond that deadline. Useful for deployments that must re-authenticate on a schedule (e.g. NIST SP 800-63B).

Version 1.2.4
-------------

Released: April 1, 2026

Security
~~~~~~~~

- **Encrypted TOTP setup secrets**: TOTP secrets generated during MFA setup are now encrypted at rest using Fernet symmetric encryption (derived from ``SECRET_KEY``) before being stored in the database. Previously, secrets were stored in plaintext in ``GenericTokenModel``. This change is fully backward compatible — any in-flight plaintext secrets from a prior version are automatically detected and handled during read.

- **JWT signing key warning**: A runtime warning is now emitted when ``JWT_ALLAUTH_SECRET_KEY`` is not configured and ``DEBUG=False``. Using Django's ``SECRET_KEY`` as the JWT signing key is insecure for production — a dedicated ``JWT_ALLAUTH_SECRET_KEY`` is strongly recommended.

- **Reduced default refresh token lifetime** from 90 days to **14 days**. The previous 90-day window was excessively long in case of token leakage. Existing installations using the old ``JWT_REFRESH_TOKEN_LIFETIME`` setting are not affected — it continues to work.

- **Forced secure cookies in production**: The refresh token cookie ``secure`` flag is now forced to ``True`` when ``DEBUG=False``, regardless of the ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SECURE`` setting. If the setting is explicitly ``False`` while in production, a warning is emitted. This prevents accidental cookie exposure over plain HTTP.

- **Rate limiting on MFA verification**: ``MFAVerifyView`` and ``MFAVerifyRecoveryView`` now enforce ``AnonRateThrottle``. Additionally, the login challenge is automatically invalidated after 5 consecutive failed verification attempts, preventing brute-force attacks on TOTP codes and recovery codes.

New Features
~~~~~~~~~~~~

- **RS256 default for new projects**: ``jwt-allauth startproject`` now generates a 4096-bit RSA key pair and configures ``SIMPLE_JWT`` with RS256 asymmetric signing by default. Keys are stored in a ``keys/`` directory (excluded from version control). If key generation is not possible, the project falls back to HS256 with a commented-out ``JWT_ALLAUTH_SECRET_KEY`` placeholder. Existing installations are not affected.

- **Configurable refresh token cookie**: ``TokenRefreshView`` now reads cookie settings (``httponly``, ``secure``, ``samesite``, ``max_age``, ``path``) from the same ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_*`` settings used by ``build_token_response()``, fixing an inconsistency where the refresh endpoint ignored user configuration. A new ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_PATH`` setting (default ``'/'``) allows restricting the cookie scope.

Deprecations
~~~~~~~~~~~~

- **Settings renamed** to the ``JWT_ALLAUTH_*`` naming convention. The old names continue to work but emit a ``DeprecationWarning`` and will be removed in a future release:

  - ``JWT_SECRET_KEY`` → ``JWT_ALLAUTH_SECRET_KEY``
  - ``JWT_ACCESS_TOKEN_LIFETIME`` → ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME``
  - ``JWT_REFRESH_TOKEN_LIFETIME`` → ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME``

Version 1.2.3
-------------

Released: January 25, 2026

Behavior and functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Projects generated via ``jwt-allauth startproject`` now configure Django's ``MIGRATION_MODULES`` so that ``jwt_allauth`` migrations are stored inside the project codebase (under ``<project_module>/migrations_external/jwt_allauth``). This improves reliability in Docker/containerized deployments where ``site-packages`` is ephemeral.

Documentation
~~~~~~~~~~~~~

- Updated installation documentation to explain how to configure ``MIGRATION_MODULES`` manually in existing projects to persist ``jwt_allauth`` migrations in version control.

Version 1.2.2
-------------

Released: December 24, 2025

Behavior and functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Admin-Managed Registration**: The email confirmation link in the admin-managed registration flow is no longer single-use. It remains valid until the user successfully sets their password. This prevents issues with email security scanners (like Outlook Safe Links) consuming the token before the user can access it. The token is now automatically deleted upon successful password completion.

- **Configurable Verification Error Page**: When an invalid or expired email verification link is accessed in the admin-managed flow, a user-friendly HTML error page is now shown instead of a 400/401 API error. This template can be customized via the `EMAIL_VERIFICATION_FAILED_TEMPLATE` key in `JWT_ALLAUTH_TEMPLATES` setting.


Version 1.2.1
-------------

Released: November 29, 2025

Bug Fixes
~~~~~~~~~
- Minor fix: resolved MFA TOTP failures in production deployments with multiple workers or threads by removing dependency on default cache backend.

Behavior and functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~

- MFA TOTP challenges and setup secrets are now stored server-side in the existing ``GenericTokenModel`` database table instead of Django's default cache backend. This improves reliability in multi-worker environments without changing the public API or required settings.

Other Changes
~~~~~~~~~~~~~

- Updated supported Python versions to 3.10+ (dropped 3.8 and 3.9).
- Extended the ``mfa`` extra to include ``fido2<2.0.0`` for broader hardware key support.
- Fixed Quick Start documentation and CI smoke test to run ``python manage.py makemigrations jwt_allauth`` before ``migrate`` in projects generated via ``jwt-allauth startproject``, avoiding migration errors involving the ``JAUser`` model.

Version 1.2.0
-------------

Released: November 17, 2025

New Features
~~~~~~~~~~~~

- **MFA TOTP**: Added REST endpoints for TOTP-based multi-factor authentication using ``django-allauth`` MFA:
   - ``POST /mfa/setup/``: returns provisioning URI (otpauth), secret, and QR code (SVG)
   - ``POST /mfa/activate/``: activates TOTP and returns recovery codes
   - ``POST /mfa/verify/``: completes login when MFA is required
   - ``POST /mfa/verify-recovery/``: completes login using one-time recovery codes
   - ``POST /mfa/deactivate/``: disables TOTP for the current user
   - ``GET /mfa/authenticators/``: lists user authenticators

   Requires enabling ``allauth.mfa`` in your project ``INSTALLED_APPS`` and running migrations.
   Configurable via ``JWT_ALLAUTH_MFA_TOTP_MODE`` setting with three modes:

     - ``'disabled'`` (default): MFA TOTP is disabled
     - ``'optional'``: Users can enable MFA TOTP but it's not required for login
     - ``'required'``: Users must enable MFA TOTP and provide TOTP code during login

- **Admin-Managed User Registration**: New registration flow controlled via ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` setting. When enabled:
    - Self-registration endpoint is disabled
    - Only users with allowed roles (configurable via ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES``) can register new users
    - New ``/user-register/`` endpoint for admin registration
    - Invited users set their own password via email verification link before gaining access
    - No authentication tokens issued during registration; one-time password setup token issued after email verification

Version 1.1.1
-------------

Released: October 11, 2025

Breaking Change
~~~~~~~~~~~~~~~

- ``JWT_ALLAUTH_USER_ATTRIBUTES`` now expects a dictionary mapping output claim names to user attribute paths (e.g., ``{"organization_id": "organization.id"}``) instead of a list of paths. This change prevents duplicate final attribute names (e.g., multiple ``id`` keys) in JWT payloads. The previous list format is still accepted for backward compatibility, but it is deprecated and may be removed in a future release.

Version 1.1.0
-------------

Released: October 7, 2025

New Features
~~~~~~~~~~~~

- Added support for including additional user attributes in refresh tokens via the ``JWT_ALLAUTH_USER_ATTRIBUTES`` setting, allowing flexible configuration of user data included in JWT payloads while maintaining the existing role assignment logic.

Bug Fixes
~~~~~~~~~

- Fixed API endpoints that incorrectly required refresh token in request payload when ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` was enabled, now properly extracting refresh tokens from cookies when configured.

- Fixed a bug that caused migrations not to run correctly in some situations.

Version 1.0.3
-------------

Released: August 5, 2025

New Features
~~~~~~~~~~~~

- New :func:`~jwt_allauth.utils.load_user` decorator that loads the complete user object from the database for stateless JWT authentication.
- Added ``JWT_ALLAUTH_COLLECT_USER_AGENT`` setting to control user agent data collection during token refresh.
- Added support for refresh tokens via HTTP cookies with the new ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` setting.
- Enhanced token refresh security by moving user agent data collection from request payload to server-side context.
- Compatibility with ``django-allauth`` 65.10.0, ``djangorestframework-simplejwt`` 5.5.1, and ``djangorestframework``  3.16.0.

Bug Fixes
~~~~~~~~~

- Improved security for token refresh operations
- Fixed a bug that caused migrations not to run correctly in some situations.


Version 1.0.2
-------------

Released: April 16, 2025

This release introduces significant improvements to the role management system and authentication configuration.

New Features
~~~~~~~~~~~~

- Added automatic role assignment in ``UserManager``:

    - ``create_superuser`` now automatically sets the role to ``STAFF_CODE``
    - ``create_user`` automatically assigns roles based on user flags:
        - ``STAFF_CODE`` for staff users
        - ``SUPER_USER_CODE`` for superusers

- Added database constraints to ensure role consistency:

    - Staff users must have ``STAFF_CODE`` role
    - Superusers must have ``SUPER_USER_CODE`` role

Minor Bug Fixes
~~~~~~~~~~~~~~~

- Automatic configuration of ``DEFAULT_AUTHENTICATION_CLASSES`` was not working when using addiotional ``REST_FRAMEWORK`` settings.
