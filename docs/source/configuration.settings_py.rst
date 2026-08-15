settings.py
===========

Configure these variables in the ``settings.py`` file of your project.

- Modules configuration

    - ``EMAIL_VERIFICATION`` - the email verification method (default: ``'none'``). One of:

        - ``'mandatory'`` (or ``True``) - no session at all until the address is confirmed: the login refuses the account and the token registration hands out is born disabled until the confirmation link is followed.
        - ``'optional'`` - the confirmation mail is sent but nothing is blocked. The account is usable from sign-up and verification governs individual features through the ``email_verified`` claim, gated with :class:`~jwt_allauth.permissions.IsEmailVerified`.
        - ``'none'`` (or ``False``) - no verification: addresses are confirmed as the account is created and no link is ever sent.

      See :doc:`email_verification`.

    - ``ACCOUNT_EMAIL_VERIFICATION`` - allauth's own setting, derived from ``EMAIL_VERIFICATION`` and normally left alone. A project that declares it instead of naming the method above still has it honoured, but the two must agree: ``EMAIL_VERIFICATION`` is this library's setting and wins, and a contradictory pair is reported with a warning at startup rather than left to produce a half-applied state.

    - ``PASSWORD_RESET_REQUEST_URL`` - address of the page on which a user asks for a password reset (default: ``None``). This library serves the endpoint that consumes a reset link, not the form that requests one, so the address has to come from the project. Used by the *account already exists* notice, which is the only warning the owner of an address gets when somebody signs up with it, and which tells them that resetting the password takes control of the account. Without it the notice still says so, but cannot link to the form.

    - ``ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS`` - Determines the expiration date of email confirmation mails (# of days) (default: ``3``).

    - ``OLD_PASSWORD_FIELD_ENABLED`` - whether to have ``old_password`` field on password change endpoint (default: ``True``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether a credential change revokes the account's sessions (default: ``True``). Applies to the password change, the password reset and the set-password step, and takes down **every** session -- the one asking for the change included, which is answered with a replacement session minted after the change -- along with every capability still outstanding and every unconfirmed secondary address. Setting it to ``False`` revokes nothing.

    - ``JWT_ALLAUTH_INVITATIONS`` - serve the invitation endpoints, so an admin can create an account for somebody else to claim (default: ``False``). Self-service registration is untouched: both ways in work at once. See :doc:`invitations`.

    - ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` - invitations **instead of** self-service registration (default: ``False``). Implies the setting above and additionally closes ``/registration/`` and social sign-up, so no account exists that an admin did not create.

    - ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME`` - access token lifetime (default: ``timedelta(minutes=30)``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME`` - refresh token lifetime (default: ``timedelta(days=14)``).

    - ``JWT_ALLAUTH_SESSION_LIFETIME`` - absolute lifetime of a session (default: ``None``, no limit). By default sessions are sliding: they stay alive for as long as they are used and expire after ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME`` of inactivity. Set a ``timedelta`` to also cap the total life of a session: rotation can no longer extend it past that deadline, the refresh endpoint then revokes the session and the user has to log in again. Useful when a policy requires periodic re-authentication (e.g. NIST SP 800-63B) or to bound the exposure of a leaked refresh token that the legitimate user never rotates again.

    - ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`` - whether every authenticated request checks that the session behind the access token is still whitelisted (default: ``False``). Enabling it makes revocation effective immediately instead of when the access token expires, at the cost of one indexed query per request. See :doc:`refresh_token`.

    - ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION`` - whether following the sign-up confirmation link opens a session on the browser that follows it, delivered as a refresh token cookie on the redirect (default: ``False``). Confirming an address added later to an account that is already usable never opens a session. Ignored when ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE = False``, as a redirect has no body to carry the token. Enabling it makes the confirmation link a credential: whoever the email reaches gets the session. See :doc:`email_verification`.

    - ``JWT_ALLAUTH_CAPABILITY_COOKIE_CSRF`` - whether the endpoints authenticated by a capability cookie (``/password/reset/set-new/`` and ``/registration/set-password/``) require a CSRF token (default: ``True``). The redirects that hand the cookie out also set the CSRF cookie, so the form has the token to send back in ``X-CSRFToken``. Turn it off only while a frontend that does not send it yet catches up: without it, the ``SameSite`` policy of the capability cookie is all that stands between another origin and those endpoints.

    - ``JWT_ALLAUTH_TOKEN_RETENTION`` - dictionary mapping a stored token purpose to the ``timedelta`` past which its rows can be deleted (default: ``{}``). Extends and overrides the built-in retentions used by ``python manage.py jwt_allauth_purge_tokens``. Example: ``{'MY_PURPOSE': timedelta(hours=6)}``.

    - ``JWT_ALLAUTH_COLLECT_USER_AGENT`` - whether to collect user agent and IP information (default: ``False``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` - whether to send refresh tokens as HTTP-only cookies instead of in the JSON response payload (default: ``True``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_HTTP_ONLY`` - whether the refresh token cookie is HTTP-only (default: ``True``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SECURE`` - whether the refresh token cookie requires HTTPS (default: ``not DEBUG``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SAME_SITE`` - SameSite policy for the refresh token cookie (default: ``'Lax'``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_MAX_AGE`` - max age of the refresh token cookie in seconds (default: derived from ``SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]`` so the cookie expires in sync with the JWT it carries). Set to ``None`` explicitly to create a session cookie instead.

    - ``JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_PATH`` - URL path scope for the refresh token cookie (default: ``'/'``). Restrict to the auth API path (e.g. ``'/jwt-allauth/'``) to avoid sending the cookie on unrelated requests.

    - ``JWT_ALLAUTH_CLIENT_IP_RESOLVER`` - optional dotted path to a callable that receives a Django ``request`` and returns the client IP address (default: ``None`` — uses built-in ``X-Forwarded-For`` / ``REMOTE_ADDR`` logic). Use this to integrate libraries like `django-ipware <https://pypi.org/project/django-ipware/>`_ that handle proxy chains more robustly. Example: ``'ipware.ip.get_client_ip'``.

    .. warning::

        The built-in IP resolver trusts the ``X-Forwarded-For`` header without validation. This header can be spoofed by any client. It is only reliable behind a **trusted** reverse proxy that overwrites or sanitises the header. If you are not behind such a proxy, provide a custom resolver or strip untrusted headers at the web-server level.

    - ``JWT_ALLAUTH_USER_ATTRIBUTES`` - dictionary mapping output claim names to dot-separated user attribute paths to include in refresh tokens (default: ``{}``). Example: ``{"organization_id": "organization.id", "area_id": "area.id"}``. The 'role' attribute is automatically included and should not be specified, and output claim names must be unique.

    - ``JWT_ALLAUTH_MFA_TOTP_MODE`` - TOTP multi-factor authentication mode (default: ``'disabled'``). Supported values:

        - ``'disabled'`` - MFA TOTP is completely disabled and cannot be configured by users.
        - ``'optional'`` - MFA TOTP is optional; users can configure it voluntarily but login does not require it.
        - ``'required'`` - MFA TOTP is mandatory; users must configure it and cannot log in without providing a TOTP code.

    - ``JWT_ALLAUTH_MFA_CHALLENGE_MAX_ATTEMPTS`` - failed MFA verifications tolerated on a single login challenge before it is invalidated (default: ``5``). Set to ``0`` to disable this limit.

    - ``JWT_ALLAUTH_MFA_MAX_ATTEMPTS`` - failed MFA verifications tolerated per user, across every challenge, within ``JWT_ALLAUTH_MFA_LOCKOUT_SECONDS`` (default: ``10``). Once spent, the user is locked out of the MFA step and ``/mfa/verify/``, ``/mfa/verify-recovery/`` and ``/login/`` answer ``429``. Set to ``0`` to disable this limit. See :doc:`mfa_totp`.

    - ``JWT_ALLAUTH_MFA_LOCKOUT_SECONDS`` - sliding window used to count failed MFA verifications, and therefore how long a locked out user waits (default: ``900``).

    - ``JWT_ALLAUTH_TOTP_ISSUER`` - custom TOTP issuer name displayed in authenticator apps like Google Authenticator (default: ``'JWT-Allauth'``). The JWT All-Auth MFA adapter is automatically configured when ``jwt_allauth`` is in ``INSTALLED_APPS``. If not set, defaults to ``'JWT-Allauth'``. Set to empty string to use the current site name instead. See :doc:`mfa_totp` for more details.

- JWT signing

    New projects created via ``jwt-allauth startproject`` are automatically configured with **RS256** asymmetric signing and a freshly generated 4096-bit RSA key pair (stored in ``keys/``, excluded from version control via ``.gitignore``). This is the recommended setup for production.

    If RSA key generation is not possible during project creation (e.g. ``cryptography`` not installed and ``openssl`` not available), the project falls back to **HS256** symmetric signing.

    - ``JWT_ALLAUTH_SECRET_KEY`` — *(HS256 only)* a dedicated secret key used exclusively for signing JWT tokens. If not set, Django's ``SECRET_KEY`` is used as a fallback. **It is strongly recommended to set this in production** — a warning is emitted at startup when running with ``DEBUG=False`` without it. This setting has no effect when using RS256/ES256 (the signing key is configured in ``SIMPLE_JWT``).

    .. warning::

        When using HS256, using ``SECRET_KEY`` for JWT signing means that a leak of ``SECRET_KEY`` (e.g. via CSRF or session internals) would also compromise all JWTs. Always set ``JWT_ALLAUTH_SECRET_KEY`` to a separate, dedicated secret, or preferably switch to RS256.

- Configuring JWT signing manually

    Projects created via ``jwt-allauth startproject`` include a ready-to-use ``SIMPLE_JWT`` configuration. For existing projects or custom setups, configure ``SIMPLE_JWT`` directly in ``settings.py``:

    **RS256 (recommended):**

    .. code-block:: python

        # settings.py — asymmetric signing
        SIMPLE_JWT = {
            "ALGORITHM": "RS256",
            "SIGNING_KEY": (BASE_DIR / "keys" / "private.pem").read_text(),
            "VERIFYING_KEY": (BASE_DIR / "keys" / "public.pem").read_text(),
        }

    To generate an RSA key pair manually:

    .. code-block:: bash

        mkdir -p keys
        openssl genrsa -out keys/private.pem 4096
        openssl rsa -in keys/private.pem -pubout -out keys/public.pem
        echo '*.pem' > keys/.gitignore

    **HS256 (simpler, single-server deployments):**

    .. code-block:: python

        # settings.py — symmetric signing
        JWT_ALLAUTH_SECRET_KEY = 'your-dedicated-jwt-secret-here'

    ``jwt-allauth`` respects any values already present in ``SIMPLE_JWT`` and will not overwrite them.

- Redirection URLs

    - ``EMAIL_VERIFIED_REDIRECT`` - the url path to be redirected once the email verified can be configured through.

    - ``PASSWORD_RESET_REDIRECT`` - the relative url with the form to set the new password on password reset.

    - ``PASSWORD_SET_REDIRECT`` - the relative url to the UI form where an invitee sets their password (used after email verification). See :doc:`invitations`.

- Templates

    - ``JWT_ALLAUTH_TEMPLATES`` - python dictionary with the following configuration:

        - ``PASS_RESET_SUBJECT`` - subject of the password reset email (default: ``email/password/reset_email_subject.txt``).
        - ``PASS_RESET_EMAIL`` - template of the password reset email (default: ``email/password/reset_email_message.html``).
        - ``EMAIL_VERIFICATION_SUBJECT`` - subject of the signup email verification sent for self-registration (default: ``email/signup/email_subject.txt``).
        - ``EMAIL_VERIFICATION`` - template of the signup email verification sent for self-registration (default: ``email/signup/email_message.html``).
        - ``ADMIN_EMAIL_VERIFICATION_SUBJECT`` - subject of the email verification sent with an invitation (default: ``email/admin_invite/email_subject.txt``).
        - ``ADMIN_EMAIL_VERIFICATION`` - template of the email verification sent with an invitation (default: ``email/admin_invite/email_message.html``).
        - ``EMAIL_VERIFICATION_FAILED_TEMPLATE`` - template rendered when an invalid or expired verification link is accessed (default: ``registration/verification_failed.html``).
        - ``ACCOUNT_EXISTS_SUBJECT`` - subject of the notice sent when somebody signs up with an address that is already in use (default: ``email/account_exists/email_subject.txt``).
        - ``ACCOUNT_EXISTS`` - template of that notice (default: ``email/account_exists/email_message.html``).

    Example:

    .. code-block:: python

        JWT_ALLAUTH_TEMPLATES = {
            'PASS_RESET_SUBJECT': 'mysite/templates/password_reset_subject.txt',
            ...
        }

- Password reset

    - ``PASSWORD_RESET_REDIRECT`` - the relative url with the form to set the new password on password reset.

    - ``PASSWORD_RESET_COOKIE_HTTP_ONLY`` - whether to set a http-only cookie (default: ``True``).

    - ``PASSWORD_RESET_COOKIE_SECURE`` - whether to set a secure cookie (default: ``not DEBUG``).

    - ``PASSWORD_RESET_COOKIE_SAME_SITE`` - same-site cookie policy (default: ``'Lax'``).

    - ``PASSWORD_RESET_COOKIE_MAX_AGE`` - maximum age of the cookie in seconds (default: ``3600``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether a credential change revokes the account's sessions (default: ``True``). Applies to the password change, the password reset and the set-password step, and takes down **every** session -- the one asking for the change included, which is answered with a replacement session minted after the change -- along with every capability still outstanding and every unconfirmed secondary address. Setting it to ``False`` revokes nothing.

- Social login

    See :doc:`social_login`. The endpoints are routed once this package is installed with its ``social`` extra (``pip install "django-jwt-allauth[social]"``) and ``allauth.socialaccount`` is in ``INSTALLED_APPS``.

    - ``JWT_ALLAUTH_SOCIAL_EMAIL_LINKING`` - whether an address a provider vouches for may resolve to an account that already holds it (default: ``True``). ``True`` links for every provider, ``False`` for none, and a list of provider ids links only for those. Linking signs the existing account in and leaves its password usable; the trust rests on the provider's claim that it verified the address, which is why it can be narrowed per provider. Only proof of control of the address earns the link -- it was confirmed, an invitation was sent to it, or the account is a staff one. An account whose address was never confirmed and which was never used is superseded instead, exactly as a duplicate registration supersedes it; one that was never confirmed but *is* in use is neither, and answers ``409`` ``local_account_unverified``. With linking off, a taken address answers ``409`` ``email_already_registered``.

    - ``JWT_ALLAUTH_SOCIAL_REQUIRE_VERIFIED_EMAIL`` - whether a provider has to vouch for the address before an account is created (default: ``True``). Turning it off only has an effect while verification is not mandatory: under ``EMAIL_VERIFICATION = 'optional'`` or ``'none'`` the account is created and signed in with no address confirmed, and under mandatory verification the sign-up is refused right afterwards and rolled back. No confirmation mail is sent on this path either way — these flows never call allauth's ``perform_login``.

    - ``JWT_ALLAUTH_SOCIAL_CALLBACK_URLS`` - redirect URIs the authorization-code endpoint will exchange a code against (default: ``None``, meaning any, with the provider left to reject a mismatch). A list turns it into an allow-list.

    allauth's own settings still govern what they always governed: ``SOCIALACCOUNT_PROVIDERS`` (where the client id and secret live), ``SOCIALACCOUNT_ADAPTER`` (jwt-allauth installs its own when the project declares none), ``SOCIALACCOUNT_AUTO_SIGNUP``, ``SOCIALACCOUNT_STORE_TOKENS`` and ``SOCIALACCOUNT_REQUESTS_TIMEOUT``. ``SOCIALACCOUNT_EMAIL_AUTHENTICATION`` is the exception: it does **not** apply to these endpoints, and ``jwt_allauth.W005`` says so at startup.

- User invitations

    See :doc:`invitations`.

    - ``JWT_ALLAUTH_INVITATIONS`` - serve ``/registration/user-register/`` and ``/registration/set-password/`` (default: ``False``), leaving self-service registration exactly as it was.

    - ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` - invitations instead of self-service registration (default: ``False``). Implies the setting above. With ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'``, ``/mfa/activate/`` issues tokens immediately after enrolment rather than sending the invitee back to the login form.

    - ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES`` - list of role codes allowed to invite. Defaults to ``[STAFF_CODE, SUPER_USER_CODE]``.

    - ``PASSWORD_SET_COOKIE_HTTP_ONLY`` - whether to set a http-only cookie for the set-password flow (default: ``True``).

    - ``PASSWORD_SET_COOKIE_SECURE`` - whether to set a secure cookie for the set-password flow (default: ``not DEBUG``).

    - ``PASSWORD_SET_COOKIE_SAME_SITE`` - same-site cookie policy for the set-password flow (default: ``'Lax'``).

    - ``PASSWORD_SET_COOKIE_MAX_AGE`` - maximum age of the set-password cookie in seconds (default: ``3600 * 24``).

- Rate limiting

    The endpoints of the library declare a throttle of their own — ``AnonRateThrottle`` on the anonymous ones
    (registration, login, password reset, MFA verification) and ``UserRateThrottle`` on the authenticated ones
    (refresh, password change, set password) — and it is **added to** the ``DEFAULT_THROTTLE_CLASSES`` of the
    project, not substituted for them. Configure ``DEFAULT_THROTTLE_CLASSES`` and ``DEFAULT_THROTTLE_RATES``
    through DRF's ``REST_FRAMEWORK`` setting as usual; a class listed there is never instantiated twice, even when
    a view asks for it as well.

    .. code-block:: python

        REST_FRAMEWORK = {
            'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.ScopedRateThrottle'],
            'DEFAULT_THROTTLE_RATES': {'anon': '60/min', 'user': '1000/day', 'registration': '5/min'},
        }

    Requesting a password reset is limited per target address on top of that, through
    allauth's ``ACCOUNT_RATE_LIMITS['reset_password']`` (``20/m/ip,5/m/key`` by default). The throttles above
    count per origin, which does not protect the mailbox on the receiving end. See :doc:`password_reset`.

    To take over completely, subclass the view: ``throttle_classes`` keeps DRF's meaning and replaces the
    defaults, and ``extra_throttle_classes = ()`` drops what the library adds.

    .. code-block:: python

        from jwt_allauth.registration.views import RegisterView

        class MyRegisterView(RegisterView):
            throttle_scope = 'registration'
            extra_throttle_classes = ()  # only the throttles of the project apply
