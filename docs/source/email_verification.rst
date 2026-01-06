Email verification
------------------

To enable the email verification, configure the email provider in your ``settings.py`` file.

.. code-block:: python

    JWT_ALLAUTH_IDENTIFIER_VERIFICATION = True
    ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
    EMAIL_HOST = ...
    EMAIL_PORT = ...
    EMAIL_HOST_USER = ...
    EMAIL_HOST_PASSWORD = ...
    EMAIL_USE_TLS = ...
    DEFAULT_FROM_EMAIL = ...

.. rubric:: Verification Flow

When ``JWT_ALLAUTH_AUTHENTICATION_METHOD = 'email'``, the registration endpoint (``POST /registration/``) behaves differently depending on whether identifier verification is enabled.

**Case 1: Verification disabled** (``JWT_ALLAUTH_IDENTIFIER_VERIFICATION = False``)

.. code-block:: bash

    POST /registration/
    {
        "email": "newuser@example.com",
        "password1": "secure_password",
        "password2": "secure_password",
        "first_name": "John",
        "last_name": "Doe"
    }

    Response (201 Created):
    {
        "refresh": "...",
        "access": "..."
    }

The user can login immediately.

**Case 2: Verification enabled** (``JWT_ALLAUTH_IDENTIFIER_VERIFICATION = True``)

.. code-block:: bash

    POST /registration/
    {
        "email": "newuser@example.com",
        "password1": "secure_password",
        "password2": "secure_password",
        "first_name": "John",
        "last_name": "Doe"
    }

    Response (201 Created):
    {
        "detail": "Verification e-mail sent.",
        "refresh": "..."
    }

The user receives an email containing a verification link.

.. code-block:: bash

    GET /registration/verification/<key>/

After verifying, the user can login normally:

.. code-block:: bash

    POST /login/
    {
        "email": "newuser@example.com",
        "password": "secure_password"
    }

    Response:
    {
        "access": "..."
    }

.. note::

   If MFA is enabled (see :doc:`mfa_totp`), login may return an MFA challenge instead of tokens.
