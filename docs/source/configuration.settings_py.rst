settings.py
===========

Configure these variables in the ``settings.py`` file of your project.

- Modules configuration

    - ``EMAIL_VERIFICATION`` - whether to enable email verification (default: ``False``).

    - ``OLD_PASSWORD_FIELD_ENABLED`` - whether to have ``old_password`` field on password change endpoint (default: ``True``).

    - ``LOGOUT_ON_PASSWORD_CHANGE`` - whether to logout from the other user sessions on password change (default: ``True``).

    - ``JWT_ACCESS_TOKEN_LIFETIME`` - access token lifetime (default: ``timedelta(minutes=30)``).

    - ``JWT_REFRESH_TOKEN_LIFETIME`` - refresh token lifetime (default: ``timedelta(days=90)``).

    - ``JWT_ALLAUTH_COLLECT_USER_AGENT`` - whether to collect user agent and IP information (default: ``False``).

    - ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` - whether to send refresh tokens as HTTP-only cookies instead of in the JSON response payload (default: ``True``).

- Redirection URLs

    - ``EMAIL_VERIFIED_REDIRECT`` - the url path to be redirected once the email verified can be configured through.

    - ``PASSWORD_RESET_REDIRECT`` - the relative url with the form to set the new password on password reset.

- Templates

    - ``JWT_ALLAUTH_TEMPLATES`` - python dictionary with the following configuration:

        - ``PASS_RESET_SUBJECT`` - subject of the password reset email (default: ``email/password/reset_email_subject.txt``).
        - ``PASS_RESET_EMAIL`` - template of the password reset email (default: ``email/password/reset_email_message.html``).
        - ``EMAIL_VERIFICATION_SUBJECT`` - subject of the signup email verification sent (default: ``email/signup/email_subject.txt``).
        - ``EMAIL_VERIFICATION`` - template of the signup email verification sent (default: ``email/signup/email_message.html``).

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
