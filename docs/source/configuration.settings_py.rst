settings.py
===========

Configure these variables in the ``settings.py`` file of your project.

- Modules configuration

    - ``EMAIL_VERIFICATION`` - whether to enable email verification (default: ``False``).

    - ``OLD_PASSWORD_FIELD_ENABLED`` - whether to have ``old_password`` field on password change endpoint (default: ``True``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether to logout from the other user sessions on password change (default: ``True``).

    - ``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION`` - whether to enable admin-only registration endpoint and set-password flow (default: ``False``). The user will receive a verification email and will need to set their password before they can login.

    - ``JWT_ACCESS_TOKEN_LIFETIME`` - access token lifetime (default: ``timedelta(minutes=30)``).

    - ``JWT_REFRESH_TOKEN_LIFETIME`` - refresh token lifetime (default: ``timedelta(days=90)``).

    - ``JWT_ALLAUTH_COLLECT_USER_AGENT`` - whether to collect user agent and IP information (default: ``False``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` - whether to send refresh tokens as HTTP-only cookies instead of in the JSON response payload (default: ``True``).

    - ``JWT_ALLAUTH_USER_ATTRIBUTES`` - dictionary mapping output claim names to dot-separated user attribute paths to include in refresh tokens (default: ``{}``). Example: ``{"organization_id": "organization.id", "area_id": "area.id"}``. The 'role' attribute is automatically included and should not be specified, and output claim names must be unique.

    - ``JWT_ALLAUTH_MFA_TOTP_MODE`` - TOTP multi-factor authentication mode (default: ``'disabled'``). Supported values:

        - ``'disabled'`` - MFA TOTP is completely disabled and cannot be configured by users.
        - ``'optional'`` - MFA TOTP is optional; users can configure it voluntarily but login does not require it.
        - ``'required'`` - MFA TOTP is mandatory; users must configure it and cannot log in without providing a TOTP code.

    - ``JWT_ALLAUTH_TOTP_ISSUER`` - custom TOTP issuer name displayed in authenticator apps like Google Authenticator (default: ``'JWT-Allauth'``). The JWT All-Auth MFA adapter is automatically configured when ``jwt_allauth`` is in ``INSTALLED_APPS``. If not set, defaults to ``'JWT-Allauth'``. Set to empty string to use the current site name instead. See :doc:`mfa_totp` for more details.

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
