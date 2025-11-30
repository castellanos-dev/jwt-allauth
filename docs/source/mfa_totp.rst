Multi-Factor Authentication (MFA TOTP)
=======================================

JWT Allauth provides comprehensive support for Time-based One-Time Password (TOTP) multi-factor authentication using ``django-allauth``. This enables users to secure their accounts with a second authentication factor beyond username and password.

Prerequisites
-------------

To use MFA TOTP, install ``django-jwt-allauth`` with the ``mfa`` extra:

.. code-block:: bash

    pip install "django-jwt-allauth[mfa]"

This will automatically install ``django-allauth[mfa]`` and all required dependencies.

Add to your ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        'jwt_allauth',
        'allauth',
        'allauth.account',
        'allauth.mfa',
    ]

The order matters: ``jwt_allauth`` should be listed before ``allauth`` apps so that the custom
adapter is properly configured.

Run migrations:

.. code-block:: bash

    python manage.py migrate

Configuration
-------------

MFA TOTP is controlled via the ``JWT_ALLAUTH_MFA_TOTP_MODE`` setting in ``settings.py``. Three modes are available.

TOTP Mode Setting
~~~~~~~~~~~~~~~~~

The ``JWT_ALLAUTH_MFA_TOTP_MODE`` setting controls how TOTP is enforced. Three modes are available:

``'disabled'`` (default)
~~~~~~~~~~~~~~~~~~~~~~~~

MFA TOTP is completely disabled. Users cannot configure or use TOTP.

.. code-block:: python

    JWT_ALLAUTH_MFA_TOTP_MODE = 'disabled'

**Behavior:**

- MFA endpoints return ``403 Forbidden``
- Login works normally without MFA requirement
- Users cannot access TOTP setup

**Use case:** Development environments or projects that don't need MFA.

``'optional'``
~~~~~~~~~~~~~~

MFA TOTP is optional. Users can enable it voluntarily but it's not required for login.

.. code-block:: python

    JWT_ALLAUTH_MFA_TOTP_MODE = 'optional'

**Behavior:**

- Users without MFA can login normally and receive tokens immediately
- Users with MFA enabled must provide a TOTP code during login
- Users can enable/disable TOTP at any time
- Login returns ``mfa_required: true`` with a ``challenge_id`` when TOTP verification is needed

**Use case:** Enhanced security with user choice.

``'required'``
~~~~~~~~~~~~~~

MFA TOTP is mandatory for all users. Users must enable TOTP and cannot disable it.

.. code-block:: python

    JWT_ALLAUTH_MFA_TOTP_MODE = 'required'

**Behavior:**

- Users without MFA cannot login (error: "Multi-factor authentication is required.")
- Users with MFA enabled must provide a TOTP code during login
- TOTP cannot be disabled (``/mfa/deactivate/`` returns ``403 Forbidden``)
- Maximum security posture

**Use case:** High-security environments (financial, healthcare, government).

Behavior Matrix
---------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Mode
     - Login (no MFA)
     - Login (with MFA)
     - /mfa/setup/
     - /mfa/deactivate/
   * - ``disabled``
     - ✅ OK
     - N/A
     - ❌ 403
     - ❌ 403
   * - ``optional``
     - ✅ OK
     - ⚠️ Challenge
     - ✅ OK
     - ✅ OK
   * - ``required``
     - ❌ 403
     - ⚠️ Challenge
     - ✅ OK
     - ❌ 403

Adapter Configuration
~~~~~~~~~~~~~~~~~~~~~

Automatic Setup
^^^^^^^^^^^^^^^

The JWT All-Auth MFA adapter is **automatically configured**. The adapter extends allauth's default MFA adapter with JWT-specific functionality.

During app initialization (in the ``ready()`` method of the AppConfig), the following happens:

1. If no ``MFA_ADAPTER`` is explicitly set in your settings, it automatically configures:

   .. code-block:: python

       MFA_ADAPTER = 'jwt_allauth.mfa.adapter.JWTAllAuthMFAAdapter'

2. This custom adapter manages TOTP (Time-based One-Time Password) configuration

**You do not need to manually set ``MFA_ADAPTER`` in your settings** unless you want to override it
with your own custom implementation.

Customizing the TOTP Issuer
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The TOTP issuer is the name that appears in authenticator apps like Google Authenticator, Microsoft Authenticator, etc.

To customize it, add this optional setting:

.. code-block:: python

    # settings.py
    JWT_ALLAUTH_TOTP_ISSUER = "My Application Name"

TOTP Issuer Priority
^^^^^^^^^^^^^^^^^^^^^

When determining what issuer name to use, the adapter follows this priority:

1. ``JWT_ALLAUTH_TOTP_ISSUER`` (if explicitly set in settings)
2. ``'JWT-Allauth'`` (default value if setting is not provided)
3. Current site name (only if ``JWT_ALLAUTH_TOTP_ISSUER`` is explicitly set to empty string or ``None``)

Examples::

    # Default (no custom setting)
    # Result: TOTP issuer = "JWT-Allauth"

    # Custom issuer
    JWT_ALLAUTH_TOTP_ISSUER = "Acme Corp"
    # Result: TOTP issuer = "Acme Corp"

    # Use site name
    JWT_ALLAUTH_TOTP_ISSUER = ""
    # Result: TOTP issuer = current site name (from SITE_ID)

For more information about MFA TOTP configuration, see :doc:`configuration.settings_py`.

Login Flow
----------

The login endpoint (``POST /login/``) behavior varies depending on the MFA mode and whether the user has TOTP enabled:

**Mode: 'disabled'**

.. code-block:: bash

    POST /login/
    {
        "email": "user@example.com",
        "password": "secure_password"
    }

    Response (all users):
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }

**Mode: 'optional'**

.. code-block:: bash

    # User WITHOUT TOTP
    POST /login/
    {
        "email": "user@example.com",
        "password": "secure_password"
    }

    Response:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }

    # User WITH TOTP
    POST /login/
    {
        "email": "admin@example.com",
        "password": "secure_password"
    }

    Response:
    {
        "mfa_required": true,
        "challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6"
    }

    # Then verify TOTP
    POST /mfa/verify/
    {
        "challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
        "code": "123456"
    }

    Response:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }

**Mode: 'required'**

.. code-block:: bash

    # User WITHOUT TOTP (Bootstrap flow instead of 403)
    POST /login/
    {
        "email": "user@example.com",
        "password": "secure_password"
    }

    Response (200 OK - Bootstrap challenge):
    {
        "mfa_setup_required": true,
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6"
    }

    # User must setup MFA first
    POST /mfa/setup/
    {
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6"
    }

    Response:
    {
        "secret": "JBSWY3DPEBLW64TMMQ======",
        "provisioning_uri": "otpauth://totp/...",
        "qr_code": "<svg>...</svg>"
    }

    # Then activate TOTP
    POST /mfa/activate/
    {
        "code": "123456",
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6"
    }

    Response (tokens issued after MFA activation):
    {
        "success": true,
        "recovery_codes": ["ABC...", "DEF..."],
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }

    # User WITH TOTP
    POST /login/
    {
        "email": "admin@example.com",
        "password": "secure_password"
    }

    Response:
    {
        "mfa_required": true,
        "challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6"
    }

    # Then verify TOTP
    POST /mfa/verify/
    {
        "challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
        "code": "654321"
    }

    Response:
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }

Registration Flow with MFA REQUIRED
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``JWT_ALLAUTH_MFA_TOTP_MODE = 'required'``, both self-service and admin-managed registration flows are modified to enforce MFA setup before token issuance:

**Self-Service Registration** (``POST /registration/``)

.. code-block:: bash

    # User registers
    POST /registration/
    {
        "email": "newuser@example.com",
        "password1": "secure_password",
        "password2": "secure_password",
        "first_name": "John",
        "last_name": "Doe"
    }

    Response (201 Created - Bootstrap challenge):
    {
        "mfa_setup_required": true,
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
        "detail": "Verification e-mail sent."
    }

    # User verifies email (if EMAIL_VERIFICATION=True)
    GET /registration/verification/<key>/

    # User proceeds with MFA setup (same as login bootstrap)
    POST /mfa/setup/
    POST /mfa/activate/
    # ... receives tokens

**Admin-Managed Registration** (``JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION = True``)

.. code-block:: bash

    # Admin creates user
    POST /registration/user-register/
    {
        "email": "inviteduser@example.com",
        "role": 300
    }

    Response (201 Created)

    # User receives email with verification link
    # User verifies email
    GET /registration/verification/<key>/

    # User sets password (returns bootstrap challenge instead of tokens)
    POST /registration/set-password/
    {
        "new_password1": "new_password",
        "new_password2": "new_password"
    }

    Response (200 OK - Bootstrap challenge):
    {
        "mfa_setup_required": true,
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
        "detail": "Password set. Please configure MFA to complete registration."
    }

    # User proceeds with MFA setup
    POST /mfa/setup/
    {
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6"
    }

    Response:
    {
        "secret": "JBSWY3DPEBLW64TMMQ======",
        "provisioning_uri": "otpauth://totp/...",
        "qr_code": "<svg>...</svg>"
    }

    # User activates TOTP
    POST /mfa/activate/
    {
        "code": "123456",
        "setup_challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6"
    }

    Response (200 OK - Tokens issued):
    {
        "success": true,
        "recovery_codes": ["ABC12345DEF67890", ...],
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..." (or in HTTP-only cookie)
    }

    # User is now fully registered and authenticated

 Key Points
 ^^^^^^^^^^

 - In both registration flows, when MFA is REQUIRED, **no tokens are issued during registration or password setup**
 - Users receive a ``setup_challenge_id`` instead, which allows access to ``/mfa/setup/`` and ``/mfa/activate/`` without authentication
 - After successful MFA activation using ``setup_challenge_id``, **tokens are always issued** via ``/mfa/activate/`` (using ``build_token_response()``), completing login/registration in a single step
 - ``build_token_response()`` respects ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` configuration for token delivery method
 - This prevents bypass of MFA requirements and ensures consistent security posture across all registration methods

 Storage Backend
 ~~~~~~~~~~~~~~~~~~~

 Setup and login challenges, as well as temporary MFA setup secrets, are stored in the database using ``GenericTokenModel`` instead of Django's cache. This means:

 - The library works correctly in multi-process / multi-worker environments without requiring a shared cache backend.
 - No additional migrations are needed, since it reuses the existing generic token table.
 - Expiration is enforced by comparing the token creation time with ``MFA_TOKEN_MAX_AGE_SECONDS``; expired tokens are cleaned up on access.

 Challenge Token TTL
 ~~~~~~~~~~~~~~~~~~~

 Setup challenges expire after 5 minutes (300 seconds). This is controlled by ``MFA_TOKEN_MAX_AGE_SECONDS`` in constants.

 If a user doesn't complete MFA setup within 5 minutes, they must re-login or re-register to get a new challenge.

Security Considerations
-----------------------

✅ **Prevents Bypass:**
- No tokens issued during registration or password setup
- MFA setup is mandatory before any API access

✅ **Consistent Across Methods:**
- Self-service and admin-managed registration behave identically
- Login and registration share the same bootstrap mechanism

 ✅ **Temporary Access Control:**
 - Setup challenges are single-purpose (MFA setup only)
 - Challenges are stored server-side in the database via ``GenericTokenModel``, not in tokens or client-side storage
 - Challenges expire after 5 minutes

✅ **Respects Configuration:**
- Cookie preferences (HTTP-only, Secure, SameSite) are honored
- Works with both JSON and cookie-based token delivery

Troubleshooting
---------------

**Challenge Expired**

.. code-block:: json

    {
        "detail": "Setup not initiated."
    }

**Solution:** User took too long. They must start from login/registration again.

**Challenge ID Not Found**

.. code-block:: json

    {
        "detail": "Authentication credentials were not provided."
    }

**Solution:** The ``setup_challenge_id`` wasn't provided or was incorrect. Include it in the request body.

**Permission Denied**

.. code-block:: json

    {
        "detail": "TOTP already activated."
    }

**Solution:** User already configured MFA. They can login and use ``/mfa/deactivate/`` (if in 'optional' mode) to reset, then re-setup.
