settings.py
===========

Configure these variables in the ``settings.py`` file of your project.

- Modules configuration

    - ``EMAIL_VERIFICATION`` - whether to enable email verification (default: ``False``).

    - ``ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS`` - Determines the expiration date of email confirmation mails (# of days) (default: ``3``).

    - ``OLD_PASSWORD_FIELD_ENABLED`` - whether to have ``old_password`` field on password change endpoint (default: ``True``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether to logout from the other user sessions on password change (default: ``True``).

    - ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` - whether to enable admin-only registration endpoint and set-password flow (default: ``False``). The user will receive a verification email and will need to set their password before they can login.

    - ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME`` - access token lifetime (default: ``timedelta(minutes=30)``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME`` - refresh token lifetime (default: ``timedelta(days=14)``).

    - ``JWT_ALLAUTH_SESSION_LIFETIME`` - absolute lifetime of a session (default: ``None``, no limit). By default sessions are sliding: they stay alive for as long as they are used and expire after ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME`` of inactivity. Set a ``timedelta`` to also cap the total life of a session: rotation can no longer extend it past that deadline, the refresh endpoint then revokes the session and the user has to log in again. Useful when a policy requires periodic re-authentication (e.g. NIST SP 800-63B) or to bound the exposure of a leaked refresh token that the legitimate user never rotates again.

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

    - ``PASSWORD_SET_REDIRECT`` - the relative url to the UI form to set the password for admin-managed registration (used after email verification).

- Templates

    - ``JWT_ALLAUTH_TEMPLATES`` - python dictionary with the following configuration:

        - ``PASS_RESET_SUBJECT`` - subject of the password reset email (default: ``email/password/reset_email_subject.txt``).
        - ``PASS_RESET_EMAIL`` - template of the password reset email (default: ``email/password/reset_email_message.html``).
        - ``EMAIL_VERIFICATION_SUBJECT`` - subject of the signup email verification sent for self-registration (default: ``email/signup/email_subject.txt``).
        - ``EMAIL_VERIFICATION`` - template of the signup email verification sent for self-registration (default: ``email/signup/email_message.html``).
        - ``ADMIN_EMAIL_VERIFICATION_SUBJECT`` - subject of the email verification sent for admin-managed invitations (default: ``email/admin_invite/email_subject.txt``).
        - ``ADMIN_EMAIL_VERIFICATION`` - template of the email verification sent for admin-managed invitations (default: ``email/admin_invite/email_message.html``).
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

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether to logout from the other user sessions on password change (default: ``True``).

- Admin-managed registration

    - ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` - enable admin-only registration endpoint and set-password flow (default: ``False``). When enabled with ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'``, the ``/mfa/activate/`` endpoint issues tokens immediately after successful MFA setup.

    - ``JWT_ALLAUTH_REGISTRATION_ALLOWED_ROLES`` - list of role codes that can register users when admin-managed registration is enabled. Defaults to ``[STAFF_CODE, SUPER_USER_CODE]``.

    - ``PASSWORD_SET_COOKIE_HTTP_ONLY`` - whether to set a http-only cookie for the set-password flow (default: ``True``).

    - ``PASSWORD_SET_COOKIE_SECURE`` - whether to set a secure cookie for the set-password flow (default: ``not DEBUG``).

    - ``PASSWORD_SET_COOKIE_SAME_SITE`` - same-site cookie policy for the set-password flow (default: ``'Lax'``).

    - ``PASSWORD_SET_COOKIE_MAX_AGE`` - maximum age of the set-password cookie in seconds (default: ``3600 * 24``).
