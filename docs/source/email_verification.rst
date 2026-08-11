Email verification
------------------

To enable the email verification, configure the email provider in your ``settings.py`` file.

.. code-block:: python

    EMAIL_VERIFICATION = True
    ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
    EMAIL_HOST = ...
    EMAIL_PORT = ...
    EMAIL_HOST_USER = ...
    EMAIL_HOST_PASSWORD = ...
    EMAIL_USE_TLS = ...
    DEFAULT_FROM_EMAIL = ...

.. note::

    With verification enabled, registering an address that is already in use is answered exactly
    like a fresh registration: its owner is notified instead of receiving a confirmation link, and
    the response carries no refresh token. See :doc:`api_endpoints` for the details and for how to
    opt out through ``ACCOUNT_PREVENT_ENUMERATION``.
