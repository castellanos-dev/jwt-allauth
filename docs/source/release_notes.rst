Release Notes
=============

Version 1.3.1
-------------

Released: August 12, 2026

Security
~~~~~~~~

- **Password change rejected for deactivated accounts**: the endpoint loaded the account straight from the database without checking ``is_active``, and it ends by handing out a session. Login and refresh both refuse a deactivated account, so this was the last way back into one: an access token issued before the deactivation could still be spent on a password change, and the response came back with a fresh, indefinitely renewable session. The account is re-read through ``load_capability_user`` now, as the reset and set-password flows already were, and a deactivated or deleted one answers ``401`` without touching the password.

- **The refresh token from sign-up is delivered as a cookie**: ``POST /registration/`` built its response by hand and put the refresh token in the JSON body, while every other endpoint of the library delivers it in the HttpOnly ``refresh_token`` cookie under ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` (the default). Sign-up is the one response a script always reads, so the longest-lived credential ended up in the hands of JavaScript — and the CSRF check on rotation was guarding something already exposed. It now goes out the same way as everywhere else; installations on ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False`` still get it in the body. Clients that read ``refresh`` from the sign-up response have to pick it up from the cookie.

Bug Fixes
~~~~~~~~~

- **The e-mail confirmation no longer answers 500 when its landing page is not routed**: the built-in "email verified" page is routed by the URLconf of ``jwt_allauth.registration``, and a project is free to wire its endpoints by hand. Reversing it then raised ``NoReverseMatch`` on a link an end user opens, rather than failing as the configuration error it is. The page is rendered in place when there is no URL to redirect to, and ``manage.py check`` reports the missing route at startup (``jwt_allauth.W001``), pointing at ``EMAIL_VERIFIED_REDIRECT``.

- **Endpoints describe themselves in the OpenAPI schema**: ``ExtraThrottlesMixin`` comes first on the MRO of every view that carries it, so its docstring became the description of the login, registration, refresh, password and MFA endpoints — the login endpoint documented the throttling system. The mixin carries no docstring now (the explanation moved to its module) and those views describe themselves. Registration also derived its ``201`` from the serializer it validates the request with, announcing ``email`` and ``first_name`` where the response actually carries the session, so a frontend reading the schema could not find the token; the responses are declared, and the endpoints authorized by a capability cookie declare that cookie and the ``X-CSRFToken`` header instead of the bearer token they reject. The annotations are applied through `drf-spectacular <https://drf-spectacular.readthedocs.io/>`_ when the new ``schema`` extra is installed, and are inert otherwise — see :doc:`api_endpoints`.

Version 1.3.0
-------------

Released: August 12, 2026

Security
~~~~~~~~

- **Setting a password revokes everything, the caller's session included**: the password change spared the session that asked for it, and neither it nor the reset touched the capabilities still outstanding — an unopened second reset link, an MFA setup challenge — or an unconfirmed secondary address queued up behind the primary one. Setting a password is the moment an account changes hands, and anything left alive is a way back in for whoever held it before. Reset, change and set-password now drop every session, every stored token bar the failed-MFA counter, and every unconfirmed non-primary address. ``/password/change/`` answers with a replacement session minted after the change (``access`` in the body, refresh token as a cookie), so the caller is not left stranded by the revocation of its own session; clients that ignored the response body have to pick the new tokens up. ``LOGOUT_ON_PASSWORD_CHANGE = False`` still opts out of all of it.

- **The 'account already exists' notice says how to take the account back**: it told the recipient that they could safely ignore it, which is only true when the sign-up attempt was an honest mistake. It now states that if it was not them and the address is theirs, resetting the password takes control of the account and signs out everybody currently using it — and links to the reset form when ``PASSWORD_RESET_REQUEST_URL`` is configured. It is the only warning the owner of an address gets when somebody registers with it, and under ``ACCOUNT_EMAIL_VERIFICATION = 'optional'`` it is what the recovery path hangs on.

New Features
~~~~~~~~~~~~

- **Optional email verification**: ``EMAIL_VERIFICATION`` now names the method — ``'mandatory'``, ``'optional'`` or ``'none'``, with ``True`` and ``False`` still accepted as the first and the last — and ``'optional'`` means what it means in allauth: *send the confirmation mail, but do not block*. It was reachable before only through allauth's ``ACCOUNT_EMAIL_VERIFICATION``, and only ``enumeration_prevented()`` consulted that, so it behaved as a ``'mandatory'`` with a different enumeration story: allauth did not block, but the login still refused the account and registration still issued a disabled token. Every session decision asks the same question now, so with ``'optional'`` the sign-up answers with usable ``access`` and ``refresh`` tokens, the login of an unconfirmed account works, and rotation works. That gives projects the usual shape of the web — account usable from sign-up, verification as a gate over features — without the design ``'mandatory'`` forces, where following the link adopts an account somebody else created with a password somebody else chose. Deployments on ``True``, ``False`` or an explicit ``'mandatory'`` / ``'none'`` are unaffected.

- **The two verification settings are reconciled at startup**: ``EMAIL_VERIFICATION`` governed the routing of the confirmation URL and whether an address is confirmed at sign-up, while allauth's ``ACCOUNT_EMAIL_VERIFICATION`` governed whether the mail is sent, and nothing kept them in step — so a pair that disagreed produced a state nobody designed. ``EMAIL_VERIFICATION = True`` with ``ACCOUNT_EMAIL_VERIFICATION = 'none'`` was the sharpest: the URL was routed, addresses were left unconfirmed and no link was ever sent to confirm them with, so no account could ever be verified. ``AppConfig.ready`` now settles on one method and makes both settings say it. ``EMAIL_VERIFICATION`` is this library's setting and wins where the two are spelled out; a project that declares only allauth's still has it honoured, and a contradictory pair is reported with a warning naming what it produces and what to set instead. A value that is not a verification method at all raises ``ImproperlyConfigured``. Nothing changes for a coherent configuration — including ``EMAIL_VERIFICATION = True`` next to an explicit ``'mandatory'`` or ``'optional'``.

- **``email_verified`` claim and ``IsEmailVerified`` permission**: every token carries whether the account has a confirmed address, written when the session starts and re-read from the database on every refresh token rotation — the frontend calls ``/refresh/`` after the user follows the link and the claim flips, with no endpoint to add for it. :class:`~jwt_allauth.permissions.IsEmailVerified` gates a view on it without touching the database, and composes with the role permissions through DRF's operators (``RegularUserPermission & IsEmailVerified``), so *regular and verified* needs no class of its own. Which endpoints it guards is the project's decision. The claim only ever turns on, so a token that has not been rotated since the confirmation denies rather than grants; tokens minted before the claim existed are denied and get it back on the next refresh.

Version 1.2.6
-------------

Released: August 12, 2026

Security
~~~~~~~~

- **Password reset is limited per target address, not only per origin**: the endpoint carried DRF's ``anon`` throttle, which counts requests per address of origin, so rotating the origin was enough to keep somebody else's inbox under a stream of reset links. allauth's ``reset_password`` limit is consumed now as well, keyed by the address being targeted (``20/m/ip,5/m/key`` by default) and consumed before the account is looked up, so an unregistered address answers ``429`` exactly like a registered one. Tune or lift it through ``ACCOUNT_RATE_LIMITS``.

- **A logout can no longer be overtaken by a refresh in flight**: rotation locks the whitelist row it consumes, deletes it and inserts the successor, while ``/logout/``, ``/logout-all/``, the reuse detection and the password flows deleted rows without any lock of their own. Under ``READ COMMITTED`` a deletion does not see a row inserted by a transaction that commits after it started, so a refresh landing at the same moment as a revocation left its successor behind: the endpoint answered *"Successfully logged out"* and the session stayed open until it expired, with no way left to close it. Every writer of the session set of a user now takes a row lock on the user first (``jwt_allauth.utils.user_sessions_lock``), which orders the two: the revocation either removes the successor or the rotation finds its token already gone. Concurrent rotations of different sessions of the same user are serialised as a consequence; they are short-lived. Backends without ``SELECT ... FOR UPDATE`` (SQLite serializes writers anyway) are unaffected.

Bug Fixes
~~~~~~~~~

- **A bearer token no longer locks a client out of the password flows**: ``/password/reset/confirm/``, ``/password/reset/set-new/`` and ``/registration/set-password/`` are authorized by the one-time cookie they are handed, and the permission behind the last two turns down any request that arrives already authenticated — it replaces ``request.user`` with the holder of the capability. A native client that attaches its bearer token to every request it makes could therefore never finish a reset, and a stale header turned the link itself into a ``401``. The three views declare no authentication class now, so an ``Authorization`` header is ignored there rather than acted upon. A missing or spent capability still answers ``401``.

- **A login whitelists one session, not two**: ``LoginSerializer`` delegated to simplejwt's implementation and then minted its own token, and since every refresh token is whitelisted as it is created, each login left two rows behind while handing out a single credential. The extra session was live until it expired and could not be closed: ``/logout/`` closes a session against its refresh token, and nobody ever received that one. Only ``/logout-all/`` cleared it. The pair is minted once now, which also stops the password from being hashed a second time on every login — the parent implementation re-authenticated with Django's ``authenticate()`` after allauth had already done it.

- **Endpoint throttles are added to the project defaults instead of replacing them**: every view that declared ``throttle_classes`` — registration, login, refresh, password change, password reset, set password and the MFA endpoints — shadowed ``DEFAULT_THROTTLE_CLASSES`` rather than adding to it, which is how DRF resolves that attribute. A project capping registration with a ``ScopedRateThrottle`` at ``5/min`` had it silently displaced by the ``60/min`` ``anon`` rate the view asked for, so the endpoints most likely to have been tightened were the ones that lost their limit. Those views declare their throttles in ``extra_throttle_classes`` now and compose them with whatever ``throttle_classes`` resolves to; a class already listed in the defaults is not instantiated twice, since two instances of one throttle consume its bucket twice. Nothing changes for a project without defaults configured, DRF's semantics are preserved for subclasses that override ``throttle_classes``, and ``extra_throttle_classes = ()`` drops the additions of the library. See :doc:`configuration.settings_py`.

- **A confirmation link confirms the address even when no password-set permission is due (admin-managed registration)**: 1.2.5 refuses that permission to an account that already has a usable password, which is what stopped an old confirmation email from being replayed into a takeover. The refusal ran before the address was confirmed, though, so the link stopped doing the one thing it is sent for: the account was left unverified, and since both login and the password reset flow require a verified address, nothing could bring it back. The address is confirmed first now and only the permission is withheld — the browser lands on ``EMAIL_VERIFIED_REDIRECT`` instead of the failure page, and the account signs in with the password it already has. The takeover stays closed: what was replayed is the permission, never the confirmation.

- **Email verification no longer answers 500 when a redirect is configured**: the confirmation view reversed the URL of the built-in "email verified" page to use as a fallback, and that page is only routed while ``EMAIL_VERIFIED_REDIRECT`` is unset, so every installation that configured its own landing page raised ``NoReverseMatch`` on the redirect. The name is only resolved now when there is no configured redirect to use.

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

- **Registration no longer discloses which addresses are registered**: signing up with a taken address answered ``400`` with *"A user is already registered with this e-mail address."*, so the endpoint could be walked through a list of addresses to learn who has an account. It now follows allauth's ``ACCOUNT_PREVENT_ENUMERATION`` (enabled by default): while email verification is mandatory — both ``EMAIL_VERIFICATION`` and allauth's ``ACCOUNT_EMAIL_VERIFICATION`` — a conflicting address gets the same ``201`` as a free one, no account is created and the owner of the address is notified by email. That response carries no ``refresh`` token — one cannot be issued for somebody else's address, and it is unusable until the address is verified anyway; see ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION`` below to open the session from the confirmation link instead. Set ``ACCOUNT_PREVENT_ENUMERATION = False``, or drop mandatory verification, to report the conflict as before; the admin-managed endpoint always reports it. The endpoint honours DRF's ``anon`` throttle rate now.

- **Pending registrations are no longer destroyed by anyone who knows the address**: validating a registration deleted every unverified ``EmailAddress`` matching it, even when the request ended in ``400`` — enough to invalidate somebody else's confirmation link, or to strip an established account of an address it was still confirming, leaving the account behind it without one. Nothing is deleted during validation any more, and an address is only taken over when the account holding it is a sign-up nobody completed (unverified, never logged into, not privileged, no verified address of its own), which is then removed as a whole, user row included.

- **Refresh token rotation is atomic**: the whitelist was read, checked, cleared and repopulated without a transaction or a row lock, so two requests presenting the same refresh token at once both whitelisted a successor — one credential turned into two live sessions, and the reuse detection that revokes a session never fired. Rotation now runs in a transaction that locks the whitelist entry before reading it and treats the deletion of that entry as the claim: only the request that removed it mints the successor, the other is handled as the replay it is. ``jti`` is unique in the database now, which also turns the previously unreachable ``IntegrityError`` guard into a real last barrier.

- **Password reset and password set capabilities are consumed atomically**: both endpoints looked the single-use token up, checked it and deleted it afterwards, so two simultaneous requests carrying the same cookie both set a password and the last writer won. The deletion is the claim now, and only the request that removed the row proceeds; the same applies when a reset link is exchanged for a capability. ``PasswordResetConfirmView`` also used to mint a capability without invalidating the previous ones, leaving one alive per reset request — only the most recent one is valid now.

- **Password reset and password set rejected for deactivated accounts**: both endpoints trusted the capability alone and never looked the account up again, so deactivating an account did not invalidate a capability already issued for it — and setting a password ends by opening a session. The account is re-read when the capability is used and a deactivated one is rejected with ``401``; the reset link and the email confirmation refuse to hand a capability out for it in the first place. The reset endpoint also let a ``DoesNotExist`` escape as a ``500`` when the account had been deleted in the meantime, where the set-password endpoint already answered ``401``.

- **CSRF enforced on the flows authenticated by a capability cookie**: ``/password/reset/set-new/`` and ``/registration/set-password/`` authenticate from a cookie, and DRF runs no CSRF check for them — it exempts its views from ``CsrfViewMiddleware`` and reinstates the check only inside ``SessionAuthentication``, which these do not use. Only the ``SameSite='Lax'`` default of the cookie stood between another origin and them, and a frontend served from a different site needs that relaxed to ``'None'``. The check now runs wherever a capability cookie is accepted, and the redirects that hand the capability out carry the CSRF cookie the frontend has to send back in ``X-CSRFToken``. The built-in password forms already do. Set ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF = False`` to opt out while a frontend catches up.

- **Refresh rejected for deactivated accounts**: rotating a refresh token now requires the account to be active. When ``is_active`` is ``False`` the refresh is rejected and the user's whitelisted refresh tokens are removed, which ends every session of the account. Previously only ``LoginView`` checked ``is_active``, so a deactivated user kept its sessions alive by refreshing.

New Features
~~~~~~~~~~~~

- **Optional session on email verification**: with ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION = True`` (default ``False``), following the sign-up confirmation link sets a refresh token cookie on the redirect, so the browser that opened the email lands on the frontend already authenticated. It is the natural place for the session that registration no longer hands out when address conflicts are hidden — control over the mailbox has just been proven, and the link is often opened on a different device from the one that filled in the form — and it applies whether or not conflicts are hidden. Off by default because it turns the confirmation link into a credential: whoever the email reaches gets the session. Confirming an address added later to an account that is already usable never opens one.

- **Optional session revocation check on access tokens**: revoking a session removes its refresh tokens from the whitelist, which stops rotation, but the access tokens already issued for it keep working until they expire (up to ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME``). Setting the new ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK = True`` (default ``False``) makes authentication check the ``session`` claim against the whitelist on every request, so ``/logout/``, a reused refresh token or any other revocation takes effect immediately, at the cost of one indexed query per request. ``jwt_allauth.authentication.JWTAllAuthAuthentication`` is now the default authentication class and applies it; ``SessionRevocationMixin`` is available for projects with their own class. The whitelist ``session`` column is indexed now, and ``jti`` is unique: run ``python manage.py makemigrations jwt_allauth && python manage.py migrate``.

- **Optional absolute session lifetime**: sessions remain sliding by default — they stay alive for as long as they are used and expire after ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME`` of inactivity — but the new ``JWT_ALLAUTH_SESSION_LIFETIME`` setting (default ``None``, no limit) caps how long a session may live in total, no matter how often it is refreshed. Refresh tokens now carry a ``session_iat`` claim, set when the session starts and preserved across rotations, so the limit is measured from the login instead of the last rotation. When it is reached the refresh endpoint revokes the whole session and answers ``401`` with code ``session_expired``; until then no token is issued with an expiration beyond that deadline. Useful for deployments that must re-authenticate on a schedule (e.g. NIST SP 800-63B).

- **Retention for the stored tokens**: a row is only dropped when the token it holds is used, and nothing uses the ones nobody comes back for — an unopened reset link, an invitation nobody accepts or an MFA challenge abandoned at the code prompt in ``GenericTokenModel``, a session left behind on a device that never logs out in the refresh token whitelist. Both tables grew without bound. The new ``python manage.py jwt_allauth_purge_tokens`` command (``--dry-run`` to count first) deletes what is past the lifetime of the flow that issued it: an expired refresh token is rejected on its own ``exp`` before the whitelist is read, and every other flow checks its own expiry too, so nothing that could still be honoured is removed and the command is safe to run on a schedule. Purposes the library does not know about are left alone and reported; declare their retention through ``JWT_ALLAUTH_TOKEN_RETENTION = {'MY_PURPOSE': timedelta(hours=6)}`` to have them purged too. The MFA challenges of a user are also cleaned up as new ones are issued.

Performance
~~~~~~~~~~~

- **Stored tokens are indexed**: ``GenericTokenModel`` had no index at all, so every single-use validation, every MFA lookup and every invalidation scanned a table that only grows. The pairs those queries narrow by — ``(token, purpose)``, ``(user, purpose)`` and ``(purpose, created)`` — are indexed now: run ``python manage.py makemigrations jwt_allauth && python manage.py migrate``.

Bug Fixes
~~~~~~~~~

- **Password reset link kept public**: ``PasswordResetConfirmView`` did not declare ``permission_classes``, so it inherited the project's ``DEFAULT_PERMISSION_CLASSES``. Where that default is ``IsAuthenticated``, the link sent by email answered ``401`` to the anonymous user clicking it and the reset flow was unusable. The view now declares ``AllowAny``, like the other password reset entry points.

- **Invalid reset link page no longer answers 500**: the page rendered for an expired or already used link reversed a URL that only exists when the built-in password UI is routed, so it raised ``NoReverseMatch`` in every project configured with its own ``PASSWORD_RESET_REDIRECT``.

- **Duplicate MFA login challenge no longer answers 500**: the challenge was looked up with ``get()``, which raises ``MultipleObjectsReturned`` if two rows ever share an id. The newest match is taken now.

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
