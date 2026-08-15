Release Notes
=============

Version 1.5.1
-------------

Released: August 15, 2026

Security
~~~~~~~~

- **A provider no longer signs in to an account that never confirmed its address.** Deciding whether to hand an existing account to whoever an identity provider vouches for used the same predicate registration uses to decide whether an account may be *destroyed*, and one of its facts is ``last_login``. Under ``EMAIL_VERIFICATION = 'optional'`` the sign-up stamps ``last_login`` itself, so every address anybody had ever typed into ``/registration/`` counted as claimed. That let a stranger register the victim's address with a password of their own choosing and wait: the victim's *Sign in with Google* was connected **into the stranger's account**, whose password stayed usable and whose address stayed unconfirmed, indefinitely. The same pre-hijacking ``JWT_ALLAUTH_INVITATIONS`` closed on the registration side, reopened through the provider.

  Two predicates now answer the two questions. :func:`jwt_allauth.accounts.account_is_claimed` is unchanged and still guards registration: ``last_login`` belongs there, because somebody has been working in that account whoever they are. :func:`jwt_allauth.accounts.mailbox_control_proven` is new and is what social login reads: a confirmed address, an invitation in flight, or a staff account — never ``last_login``, which cannot prove control of a mailbox no matter when it is stamped.

Bug Fixes
~~~~~~~~~

- **Logout works in the default configuration.** ``POST /logout/`` re-read ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` with a default of ``False`` while every endpoint that *issues* a refresh token reads ``jwt_allauth.utils.refresh_token_as_cookie()``, whose default is ``True``. With the setting left undeclared — the case every new project is in — the token went out as an HttpOnly cookie and logout looked for it in the request body, which a browser client cannot fill: the cookie is out of reach of scripts and the login response carries only ``access``. Logout answered ``400 REQUIRED`` on ``refresh`` and closed nothing, leaving the whitelist row and a thirty-day cookie alive on whatever machine the session was opened on. The view now reads the same helper as everyone else, so the two cannot disagree again. Documented behaviour is unchanged — :doc:`api_endpoints` already described the cookie as the default source; it is the code that now matches it.

Compatibility
~~~~~~~~~~~~~

- **A social login against a local account that is in use and unconfirmed now answers** ``409`` ``local_account_unverified`` instead of linking. Only reachable where verification is not mandatory. Installations that relied — without knowing it — on such an account being linked will see the refusal; the way through is for the account to confirm the address it already has the mail for, after which the same login links as before. The account is deliberately **not** superseded: under ``'optional'`` and ``'none'`` an unconfirmed account is an ordinary, fully usable one, and deleting it would trade an account takeover for a data loss. Nothing is created or removed on the refusal. See :doc:`social_login`.

- **Everything else about linking is unchanged.** A confirmed address still links and still keeps its password; an invited account still links, as the invitation asked; an account nobody ever claimed is still superseded; ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING`` still narrows all of it per provider.

- **New public function** :func:`jwt_allauth.accounts.resolve_email_for_provider`, alongside the existing :func:`~jwt_allauth.accounts.resolve_email`, which is untouched — including the ``_superseded_accounts`` override point on the registration serializers.

- **No new model and no migration.**

Version 1.5.0
-------------

Released: August 15, 2026

New Features
~~~~~~~~~~~~

- **Social login**: sign in through any provider ``django-allauth`` registers, either with a credential the client obtained from the provider (``POST /social/<provider>/token/``) or with an authorization code exchanged server side, PKCE included (``POST /social/<provider>/code/``). One generic endpoint per flow serves every provider — the provider id travels in the URL — so there is no view to subclass and no adapter to name. Providers can also be connected to and disconnected from an existing account, and listed. The session is minted the way every other session is, so it carries its device, appears on the whitelist and answers to ``/logout/``, rotation and replay detection. Install the new ``social`` extra: ``pip install "django-jwt-allauth[social]"``. See :doc:`social_login`.

- **A provider signs in the account that already holds the address, without wiping its password.** When a provider vouches for an address an established local account holds — one whose address was confirmed, or which has been used — the two are taken to be the same person: the provider is connected and the password stays usable, so both ways in keep working. An address held only by a sign-up that was never confirmed and never used is superseded instead, exactly as a duplicate registration supersedes it. This is deliberately not allauth's behaviour: ``SOCIALACCOUNT_EMAIL_AUTHENTICATION`` wipes the local password every time it matches an account by address; the match it makes is **discarded** here, so this rule is the one that decides. Use ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING`` (default ``True``, or a list of provider ids) instead.

- **A social login does not skip the second factor.** An account with an authenticator gets the same ``mfa_required`` challenge ``/login/`` returns, completed at the same ``/mfa/verify/``, and ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'`` bootstraps enrolment for a social sign-up as it does for any other.

- **Invitations without closing the public sign-up**: ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` has always meant two things at once — an admin can create accounts, *and* nobody can create their own — which ruled out the ordinary arrangement of customers signing themselves up while staff are invited. ``JWT_ALLAUTH_INVITATIONS = True`` asks for the first half only: ``/registration/user-register/`` and ``/registration/set-password/`` are served and ``/registration/`` keeps answering, as does social sign-up. Both ways in share the confirmation link, and an invitation is recorded as such when it is sent, so only an invitation can be exchanged for the capability to set a first password. See :doc:`invitations`.

- **An invitation in flight holds on to its address.** An invited account looks exactly like an abandoned sign-up — no password, never used, address unconfirmed — which is what the public sign-up is allowed to supersede. It is now excluded from that while the link lives: posting an invitee's address to ``/registration/`` no longer destroys the account, the role granted with it and the link, silently. The reservation ends with the link (``ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS``): an expired invitation frees the address, so a dead invitation cannot hold one hostage.

- **Two new startup checks**: ``jwt_allauth.W004`` when a provider is configured but the installation cannot serve it — the ``social`` extra missing, so the endpoints are not routed, or no provider app carrying credentials, so they answer ``404`` — and ``jwt_allauth.W005`` when ``SOCIALACCOUNT_EMAIL_AUTHENTICATION`` is declared, globally or per provider, and these endpoints override it. Neither says anything until the project asks for a provider.

Compatibility
~~~~~~~~~~~~~

- **The social endpoints are routed only when** ``allauth.socialaccount`` **is in** ``INSTALLED_APPS`` **and its dependencies are importable.** ``jwt-allauth startproject`` has always written that app into generated projects, so an installation can have the app without the extra; it keeps working untouched, the endpoints stay unrouted rather than failing on the first request, and ``jwt_allauth.W004`` reports the shortfall — but only once the project configures a provider, so a generated project that never asked for social login boots silently.

- **A default** ``SOCIALACCOUNT_ADAPTER`` **is installed** when ``allauth.socialaccount`` is present and the project declares none. It closes social sign-up under ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION``, and refuses to disconnect the last provider of an account with no usable password — allauth's default allows it, which locks the owner out for good. A project with an adapter of its own is left alone.

- **``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` is unchanged** and now implies ``JWT_ALLAUTH_INVITATIONS``. A project already using it needs to do nothing: closed registration still refuses ``/registration/``, still shuts social sign-up, and still turns down a confirmation key with no invitation behind it.

- **New settings**: ``JWT_ALLAUTH_INVITATIONS``, ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING``, ``JWT_ALLAUTH_SOCIAL_REQUIRE_VERIFIED_EMAIL`` and ``JWT_ALLAUTH_SOCIAL_CALLBACK_URLS``. See :doc:`configuration.settings_py`.

- **Address ownership is now resolved against the column as allauth writes it** — lower case — instead of case-insensitively, so the lookup uses the index allauth ships rather than scanning the table on every sign-up and every social login. allauth folds the case on the way in and reads it back the same way, so nothing it wrote is affected. Rows inserted around it, in mixed case (a data import, a hand-written fixture), stop matching: a sign-up for that address is answered as if it were free, which yields a second account rather than taking the first one over. Lower-case them before upgrading if that applies to you.

- **Invitations sent before this release keep working.** They are stored with a purpose of their own from now on; the rows already in the database carry the generic confirmation purpose, and under ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` — the only configuration that could have produced one — they are still accepted until they expire. No migration and no backfill: the rows are short-lived by design (``ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS``). They do not reserve their address, which only the new purpose does.

- **The confirmation link is steadier under** ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION``. A link opened twice — a scanner, a browser prefetch, a forwarded mail — lands on the same page both times instead of a bare ``404`` on the second, and a deactivated account no longer has its address confirmed by a link the flow already refuses to do anything else with. Neither ever granted a session or a capability.

- **A provider is not connected to an existing account until its second factor is in.** Signing in through a provider already returned an ``mfa_required`` challenge instead of a session, but the ``SocialAccount`` row and ``last_login`` were written first — on the strength of the first factor alone, and durably: once the row exists the provider reaches that account by uid with no address check at all. The connection is now withheld until the challenge is answered. A social **sign-up** is unchanged: there is no established account to attach to, and the enrolment challenge ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'`` hands a new account needs that account to exist.

- **``POST /registration/user-register/`` is throttled** with ``UserRateThrottle`` on top of the project defaults. The role check bounds who may invite, not how fast; the request sends mail to an address of its choosing and reports whether that address is in use.

- **The** ``social`` **extra is probed by everything it installs** — ``requests``, ``oauthlib`` and ``cryptography`` — not by ``requests`` alone. A host carrying ``requests`` for unrelated reasons used to route the endpoints, keep ``jwt_allauth.W004`` quiet, and fail with ``ModuleNotFoundError`` on the first credential.

- **``jwt-allauth startproject`` writes the RS256 signing key readable only by its owner.** It was created at the process umask — ``0644`` on most hosts, inside a ``0755`` directory — and it signs every access token the project issues; authentication is stateless by default, so a token minted with that key is accepted without a query. Existing projects are not touched by an upgrade: run ``chmod 700 keys && chmod 600 keys/private.pem``, and rotate the key if the directory was ever readable by anyone you would not hand it to.

- **Provider credentials are declared sensitive.** ``id_token``, ``access_token``, ``code`` and ``code_verifier`` are masked in tracebacks, the ``django.request`` log and the mail to ``ADMINS``, as passwords already were.

- **``RefreshToken.for_user`` accepts an optional** ``email_verified``. It is additive — omitted, the token asks the database as before — and lets a caller that has just checked hand the answer on instead of paying for the query twice. ``jwt_allauth.social.flows.authenticate_social_login`` now returns ``(user, email_verified)`` for that reason; it is new in this release, so nothing depended on the old shape. ``RefreshToken.set_email_verified`` takes the same optional argument, and is called with it only when a caller supplied one — so a subclass that overrides the one-argument form keeps working.

- **The** ``social`` **extra requires allauth 65.9**, like the ``mfa`` extra, while the core dependency floor is unchanged at 65.5. A project pinned to allauth 65.5–65.8 that adds ``[social]`` will hit a resolution conflict on upgrade and has to move the pin.

- **No new model and no migration.** Both flows are driven by the client, so there is no OAuth ``state`` for the server to store.

Documentation
~~~~~~~~~~~~~

- **New page** — :doc:`invitations`, replacing *Admin-managed registration*: the flow under the name people look for, what the confirmation link is worth, and how an invitation is told apart from a sign-up. The old page is kept as a pointer.

- **New page** — :doc:`social_login`: the two flows, the linking decision and the trust it places in the provider, and what the feature deliberately does not cover.

- The README and the documentation index no longer say social authentication is unimplemented.

Version 1.4.1
-------------

Released: August 14, 2026

Bug Fixes
~~~~~~~~~

- **A session opened through MFA records the device it came from**: the three endpoints that finish an MFA flow mint the session themselves instead of going through the login view, and none of them collected the user agent. Every MFA-completed login landed in the whitelist as a row with no browser, no operating system and no IP, so an installation listing a user's sessions had nothing to show for them and nothing to tell a familiar device from a new one. ``/mfa/verify/``, ``/mfa/verify-recovery/`` and the enrolment that opens the session under ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'`` now record it the way login, refresh and password change already did. Only installations on ``JWT_ALLAUTH_COLLECT_USER_AGENT = True`` are affected; nothing is backfilled for sessions already open.

Version 1.4.0
-------------

Released: August 14, 2026

New Features
~~~~~~~~~~~~

- **Any user model**: ``jwt_allauth.JAUser`` is no longer required. The ``role`` claim is read from a ``role`` field when the user model has one, and derived from ``is_staff`` / ``is_superuser`` when it does not — so a project that cannot swap ``AUTH_USER_MODEL`` can adopt the library with nothing to migrate. Staff and superusers keep the access :class:`~jwt_allauth.permissions.BasePermission` grants them either way. Roles of the project's own still need a field, and the admin-managed registration endpoint drops its ``role`` input when there is nowhere to write it. See :doc:`configuration.user_model`.

- **RoleMixin**: adds the ``role`` field to a user model that already exists, in one migration. **Existing staff rows must be backfilled in that same migration**, or they drop to a regular user on their next login — :doc:`configuration.user_model` carries the code. ``JAUser`` is the mixin already applied and is unchanged; no migration comes out of this release for projects on it.

- **Startup checks for a** ``role`` **field that means something else**: ``manage.py check`` now reports a ``role`` on the user model that cannot serve as the claim — an error when it is a relation (no token would encode), a warning when it is not an integer (staff would silently lose access).

Compatibility
~~~~~~~~~~~~~

- **Django 6.0 and 6.1 are supported.** Tested from the Django 4.2 floor under Python 3.10 through to Django 6.1 under Python 3.13.

- **Dependencies no longer carry upper bounds**, so a new Django, DRF, allauth or Simple JWT release cannot block installation. ``manage.py check`` reports an allauth or Simple JWT major newer than this release was tested against (``jwt_allauth.W003``); ``SILENCED_SYSTEM_CHECKS`` turns it off.

- **The** ``mfa`` **extra now requires allauth 65.9** (was 65.5). Earlier allauth asks for ``fido2`` with no upper bound, and fido2 2.0 removed a flag it depends on, so that combination raised ``AttributeError`` on any request touching ``allauth.mfa``. **A project pinned to allauth 65.5–65.8 with the** ``mfa`` **extra will hit a resolution conflict on upgrade and has to move the pin.** The core dependency floor is unchanged at 65.5.

- **An empty nullable** ``role`` **now reads as the account's staff flags** instead of ``null``. ``JAUser`` and ``RoleMixin`` declare the field ``null=False``, so neither is affected. A project with a nullable ``role`` of its own will see staff accounts whose column was never filled regain the access the permission classes have always documented; nobody loses access.

- **The package declares its MIT licence** in its published metadata, which it had never done.

Documentation
~~~~~~~~~~~~~

- **New page** — :doc:`refresh_token_theft`: why rotating refresh tokens does not detect theft on its own, and the four ways an implementation of reuse detection fails silently.

- ``SECURITY.md`` gives vulnerability reports a private channel; ``CONTRIBUTING.md`` covers the test matrix.

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
