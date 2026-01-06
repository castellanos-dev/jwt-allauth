Phone verification
------------------

To enable phone authentication and verification, configure the following in your ``settings.py`` file:

.. code-block:: python

    # Set phone as the primary authentication method
    JWT_ALLAUTH_AUTHENTICATION_METHOD = 'phone'

    # Configure SMS backend (defaults to Console backend for development)
    JWT_ALLAUTH_SMS_BACKEND = 'jwt_allauth.sms.backends.console.ConsoleSMSBackend'

    # Optional: SMS backend options (API keys, etc.)
    JWT_ALLAUTH_SMS_OPTS = {
        'API_KEY': 'your-api-key',
    }

    # Optional: Customize verification message
    JWT_ALLAUTH_SMS_VERIFICATION_MESSAGE = 'Your code is {code}'

    # Optional: Expiration time in seconds for confirmation codes (default: 300 = 5 minutes)
    JWT_ALLAUTH_PHONE_CONFIRMATION_EXPIRE_SECONDS = 300

.. rubric:: Verification Flow

When ``JWT_ALLAUTH_AUTHENTICATION_METHOD = 'phone'``, the registration endpoint (``POST /registration/``) can require SMS verification depending on ``JWT_ALLAUTH_IDENTIFIER_VERIFICATION``.

**Case 1: Verification disabled** (``JWT_ALLAUTH_IDENTIFIER_VERIFICATION = False``)

.. code-block:: bash

    POST /registration/
    {
        "phone_number": "+1234567890",
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

The phone number is treated as verified during registration and the user can login immediately.

**Case 2: Verification enabled** (``JWT_ALLAUTH_IDENTIFIER_VERIFICATION = True``)

.. code-block:: bash

    POST /registration/
    {
        "phone_number": "+1234567890",
        "password1": "secure_password",
        "password2": "secure_password",
        "first_name": "John",
        "last_name": "Doe"
    }

    Response (201 Created):
    {
        "detail": "Verification SMS sent.",
        "refresh": "..."
    }

The user receives an SMS with a 6-digit verification code. They must verify the phone number:

.. code-block:: bash

    POST /registration/verify-phone/
    {
        "phone_number": "+1234567890",
        "code": "123456"
    }

    Response (200 OK):
    {
        "detail": "Phone number verified.",
        "refresh": "...",
        "access": "..."
    }

After verification, the user is authenticated and can access protected endpoints.

If the code expires, you can request a new one:

.. code-block:: bash

    POST /registration/resend-phone/
    {
        "phone_number": "+1234567890"
    }

.. note::

   If MFA is enabled (see :doc:`mfa_totp`), login may return an MFA challenge instead of tokens.
