Welcome to JWT Allauth
======================

JWT Allauth delivers **SIMPLE** authentication for the Django REST module, based on robust frameworks configured in an **efficient** and stateless way through **JWT** access/refresh token architecture. The token whitelisting system ensures granular control over user sessions while maintaining minimal database overhead.

With **JWT Allauth**, gain peace of mind through enterprise-grade security while dedicating your energy to building your app's unique value proposition.


Features
--------

- **Low database load**: Designed to minimize database queries through stateless JWT token authentication.
- Token whitelisting system: Implements a refresh token whitelist tied to specific device sessions.
- **Enhanced security**: Enables revoking access to specific devices or all devices simultaneously.
- Automatic token renewal: Active sessions for extended periods without reauthentication, ideal for **mobile apps**.
- Email verification: Includes a full **REST email verification** system during user registration.
- Comprehensive user management: Features password recovery, email-based authentication, and session logout.
- **Effortless setup**: Get your project up and running with a single command.


Quick Start
-----------

Install using ``pip``...

    pip install django-jwt-allauth

You can quickly start a new Django project with JWT Allauth pre-configured using the `startproject` command:

    jwt-allauth startproject myproject

This will create a new Django project called `myproject` with JWT Allauth pre-configured. Then:

    cd myproject
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver

Available options:
- `--email=True` - Enables email configuration in the project
- `--template=PATH` - Uses a custom template directory for project creation


Why whitelisting?
-----------------

The refresh token whitelist tracks devices **authorized by the user**, stored in the database to verify refresh tokens during access token renewal requests.

This system empowers users to **revoke access** to stolen/lost devices or log out of all sessions simultaneously. Refresh tokens are regenerated upon each use, ensuring active session tracking. If a refresh token is reused, the system invalidates both tokens and terminates the session tied to the compromised device.

Refresh token auto-renewal enables extended active sessions without repeated logins—ideal for **mobile apps**, where users shouldn’t need to reauthenticate every time they open the app.

Access tokens provide short-lived authentication credentials (via JWT), enabling stateless API access. This approach **minimizes database load** by eliminating per-request database queries.


Email verification
------------------

To enable the email verification, configure the email provider in your ``settings.py`` file.

    EMAIL_VERIFICATION = True
    EMAIL_HOST = ...
    EMAIL_PORT = ...
    EMAIL_HOST_USER = ...
    EMAIL_HOST_PASSWORD = ...
    EMAIL_USE_TLS = ...
    DEFAULT_FROM_EMAIL = ...


Redirection URLs
----------------

The relative url to be redirected once the email verified can be configured through:

    EMAIL_VERIFIED_REDIRECT = ...

The relative url with the form to set the new password on password reset:

    PASSWORD_RESET_REDIRECT = ...

If not configured, users will be redirected to the default password reset form at ``/jwt-allauth/password/reset/default/``. This form provides a modern, responsive interface for password reset with proper form validation and error handling.


Templates
---------

The templates can be configured in a JWT_ALLAUTH_TEMPLATES dictionary:

    - ``PASS_RESET_SUBJECT`` - subject of the password reset email (default: ``email/password/reset_email_subject.txt``).
    - ``PASS_RESET_EMAIL`` - template of the password reset email (default: ``email/password/reset_email_message.html``).
    - ``EMAIL_VERIFICATION_SUBJECT`` - subject of the signup email verification sent (default: ``email/signup/email_subject.txt``).
    - ``EMAIL_VERIFICATION`` - template of the signup email verification sent (default: ``email/signup/email_message.html``).

Example:

    JWT_ALLAUTH_TEMPLATES = {
        'PASS_RESET_SUBJECT': 'mysite/templates/password_reset_subject.txt',
        ...
    }


Acknowledgements
----------------
This project began as a fork of django-rest-auth. Thanks to the authors for their great work.
