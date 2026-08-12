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

    Since registration hands out no session in that mode, set
    ``JWT_ALLAUTH_SESSION_ON_EMAIL_VERIFICATION = True`` to have the confirmation link open one
    instead: the redirect then carries a refresh token cookie for the browser that followed it.

Mandatory or optional
"""""""""""""""""""""

``EMAIL_VERIFICATION`` names the method:

``'mandatory'`` (or ``True``)
    No session at all until the address is confirmed. The login refuses the account, the token
    registration hands out is born disabled, and the confirmation link is what turns it on.

``'optional'``
    The confirmation mail is sent, but nothing is blocked. Sign-up answers with usable ``access``
    and ``refresh`` tokens, the login works, and verification governs individual features through
    the ``email_verified`` claim rather than the session itself. This is the usual shape of the web,
    and it avoids making the confirmation link a transfer of ownership — under ``'mandatory'``,
    whoever opens the mail adopts an account somebody else created, with the password that somebody
    else chose.

``'none'`` (or ``False``)
    No verification. Addresses are confirmed as the account is created and no link is ever sent.

.. code-block:: python

    EMAIL_VERIFICATION = 'optional'

.. note::

    allauth's ``ACCOUNT_EMAIL_VERIFICATION`` is derived from this and is normally left alone. A
    project that declares it instead still has it honoured — that is how ``'optional'`` was reachable
    before ``EMAIL_VERIFICATION`` could name it — but the two must agree. They govern different
    halves of the feature, so a contradictory pair used to produce a state nobody designed:
    ``EMAIL_VERIFICATION = True`` with ``ACCOUNT_EMAIL_VERIFICATION = 'none'``, for instance, left
    every address unconfirmed and never sent a link to confirm it with. Such a pair is now reconciled
    at startup and reported with a warning.

Gating features on the claim
""""""""""""""""""""""""""""

Every token carries ``email_verified``. It is written when the session starts and re-read from the
database on every refresh token rotation, so a frontend that calls ``/refresh/`` after the user
follows the link sees it flip — there is no endpoint to call for it.

.. code-block:: python

    from jwt_allauth.permissions import IsEmailVerified

    class InviteTeammateView(APIView):
        permission_classes = [IsEmailVerified]

It composes with the role permissions through DRF's operators, so *regular and verified* needs no
class of its own:

.. code-block:: python

    permission_classes = [RegularUserPermission & IsEmailVerified]

The claim only ever goes from ``False`` to ``True`` for a given address, so a token that has not
been rotated since the confirmation denies access it should by now be granting — never the other
way round. It fails closed by construction, and that also covers tokens minted before the claim
existed: their holders get it back on the next refresh.

Taking an account back
""""""""""""""""""""""

With ``'optional'``, an account can be signed up for with an address whose owner never asked for
it, and used before the address is confirmed. Two things make that recoverable, and both are
built in:

- The owner is told. The *account already exists* mail — the only notice they get — says that if
  it was not them and the address is theirs, resetting the password takes control of the account.
  Set ``PASSWORD_RESET_REQUEST_URL`` so it can link to the form that starts the reset.
- Setting a password revokes everything. Reset, change and set-password each take down every
  session (the caller's included), every capability still outstanding and every unconfirmed
  secondary address, so nobody who held the account before keeps a way back in. Setting
  ``LOGOUT_ON_PASSWORD_CHANGE = False`` opts out of that, and out of this guarantee with it.
