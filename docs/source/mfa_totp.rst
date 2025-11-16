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

For detailed information about the adapter implementation, see :doc:`jwt_allauth.mfa.adapter`.

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

API Endpoints
-------------

The following endpoints are available for MFA management (requires ``allauth.mfa`` to be installed):

Setup and Activation
~~~~~~~~~~~~~~~~~~~~~

**POST /mfa/setup/** ``[Authenticated]``

  Initiates TOTP setup. Returns provisioning URI, secret, and QR code (SVG format).

  Example response:

  .. code-block:: json

      {
          "secret": "JBSWY3DPEBLW64TMMQ======",
          "provisioning_uri": "otpauth://totp/example.com:user%40example.com?secret=...",
          "qr_code": "<svg>...</svg>"
      }

  Available in modes: ``'optional'``, ``'required'``

**POST /mfa/activate/** ``[Authenticated]``

  Activates TOTP after the user scans the QR code or enters the secret. Requires a valid 6-digit TOTP code.

  Request:

  .. code-block:: json

      {
          "code": "123456"
      }

  Response:

  .. code-block:: json

      {
          "success": true,
          "recovery_codes": [
              "ABC12345DEF67890",
              "GHI12345JKL67890",
              "..."
          ]
      }

  Available in modes: ``'optional'``, ``'required'``

Verification
~~~~~~~~~~~~~

**POST /mfa/verify/** ``[No Authentication]``

  Completes login when MFA is enabled. Requires a valid 6-digit TOTP code and a challenge ID obtained from login.

  Request:

  .. code-block:: json

      {
          "challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
          "code": "654321"
      }

  Response:

  .. code-block:: json

      {
          "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
      }

  Available in all modes when user has MFA enabled.

**POST /mfa/verify-recovery/** ``[No Authentication]``

  Completes login using a recovery code when the user doesn't have access to their TOTP device.

  Request:

  .. code-block:: json

      {
          "challenge_id": "a1b2c3d4-e5f6-4a8b-9c0d-e1f2a3b4c5d6",
          "recovery_code": "ABC12345DEF67890"
      }

  Response:

  .. code-block:: json

      {
          "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
      }

  Available in all modes when user has MFA enabled.

Management
~~~~~~~~~~

**POST /mfa/deactivate/** ``[Authenticated]``

  Disables TOTP for the authenticated user. Requires the user's password.

  Request:

  .. code-block:: json

      {
          "password": "user_password"
      }

  Response:

  .. code-block:: json

      {
          "success": true
      }

  Available in mode: ``'optional'`` only. Returns ``403 Forbidden`` in ``'required'`` mode.

**GET /mfa/authenticators/** ``[Authenticated]``

  Lists all authenticators (TOTP and recovery codes) for the authenticated user.

  Response:

  .. code-block:: json

      [
          {
              "id": 1,
              "type": "totp",
              "created_at": "2025-01-15T10:30:00Z",
              "last_used_at": "2025-01-15T14:22:00Z"
          },
          {
              "id": 2,
              "type": "recovery_codes",
              "created_at": "2025-01-15T10:30:00Z",
              "last_used_at": null
          }
      ]

  Available in modes: ``'optional'``, ``'required'``

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

    # User WITHOUT TOTP
    POST /login/
    {
        "email": "user@example.com",
        "password": "secure_password"
    }

    Response (403 Forbidden):
    {
        "detail": "Multi-factor authentication is required."
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
