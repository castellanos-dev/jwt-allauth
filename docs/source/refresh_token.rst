Refresh token
=============

Since this library is security and performance based, the authentication is performed in a nearly stateless way,
which means the user information is never loaded from the database to authenticate a request — only the session
of the access token is checked against the whitelist, and that check can be disabled (see `Session revocation`_).
The refresh token class can be
enhanced to incorporate additional data within its payload. This supplementary
information will automatically propagate to the access tokens during their generation. Additional user attributes can be included via the ``JWT_ALLAUTH_USER_ATTRIBUTES`` setting. By embedding such data
directly in the tokens, this approach reduces reliance on frequent database queries, thereby alleviating server load.
Importantly, the refresh token whitelist mechanism ensures this strategy maintains robust security standards, as
compromised or outdated refresh tokens can be promptly invalidated when necessary.

Every rotation (i.e. every call to the refresh endpoint) re-reads the user from the database and regenerates the
``role`` claim and the ``JWT_ALLAUTH_USER_ATTRIBUTES`` claims from it, so privilege changes take effect on the next
refresh instead of surviving until the refresh token expires. Rotation is also refused (and the user's refresh tokens
are removed from the whitelist) when the account is no longer active.

The following constants should be included in the settings.py file:

    - ``JWT_ALLAUTH_REFRESH_TOKEN`` - refresh token class (default: ``jwt_allauth.tokens.tokens.RefreshToken``).

    - ``JWT_ALLAUTH_USER_ATTRIBUTES`` - dictionary mapping output claim names to user attribute paths to include in tokens (default: ``{}``). Example: ``{"organization_id": "organization.id", "area_id": "area.id"}``. The 'role' attribute is automatically included and should not be specified.

    - ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` - whether to send refresh tokens as HTTP-only cookies instead of in the JSON response payload (default: ``True``).

    - ``JWT_ALLAUTH_SESSION_LIFETIME`` - absolute lifetime of a session (default: ``None``, no limit).

    - ``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK`` - whether access tokens are checked against the refresh token whitelist on every request (default: ``True``).

Session revocation
------------------

Revoking a session removes its refresh tokens from the whitelist, which stops any further rotation. Access
tokens, however, are self-contained: nothing in them says whether the session they belong to is still alive.
Every access token already handed out therefore has to be rejected explicitly, otherwise it keeps working
until it expires on its own — up to ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME`` after the revocation.

That is what the authentication classes in :mod:`jwt_allauth.authentication` do: on each authenticated request
they check that the ``session`` claim of the access token still matches a whitelisted refresh token, and answer
``401`` with code ``token_not_valid`` when it does not. ``jwt_allauth.authentication.JWTAllAuthAuthentication``
is configured as the default authentication class, and it keeps the stateless user of simplejwt's
``JWTStatelessUserAuthentication`` — the user table is still never hit. The check applies to every way a
session ends: ``/logout/``, ``/logout-all/``, a password change or reset, the absolute session lifetime, a
deactivated account, and the detection of a reused refresh token.

Reusing a rotated refresh token is the case that motivates it. Rotation makes the replay detectable, but the
attacker that replayed the token has already obtained a fresh access token; without this check, revoking the
session locks out the legitimate user immediately (its next rotation fails) while the attacker keeps working
until its access token expires.

If a project sets its own ``DEFAULT_AUTHENTICATION_CLASSES``, mix
``jwt_allauth.authentication.SessionRevocationMixin`` into the authentication class to keep revocation
effective:

.. code-block:: python

    from rest_framework_simplejwt.authentication import JWTAuthentication

    from jwt_allauth.authentication import SessionRevocationMixin


    class MyAuthentication(SessionRevocationMixin, JWTAuthentication):
        pass

A warning is emitted at startup when ``DEFAULT_AUTHENTICATION_CLASSES`` uses simplejwt's classes directly, since
revocation would then have no effect on access tokens.

The check costs one indexed query per authenticated request. Setting
``JWT_ALLAUTH_ACCESS_TOKEN_SESSION_CHECK = False`` removes it and restores fully stateless authentication; with
that setting, keep ``JWT_ALLAUTH_ACCESS_TOKEN_LIFETIME`` short, as it becomes the window during which a revoked
session remains usable.

Tokens without a ``session`` claim are not affected — the one-time capabilities issued by the password reset and
email confirmation flows carry their own single-use validation.

Session lifetime
----------------

Sessions are sliding by design: every rotation moves the expiration forward, so a session that keeps being
used stays alive indefinitely, and one that stops being used dies after ``JWT_ALLAUTH_REFRESH_TOKEN_LIFETIME``
of inactivity. This is what allows mobile clients to stay logged in without asking the user for credentials
again. Leaked tokens are handled by revocation: reusing a rotated token destroys the whole session, and
``/logout/``, ``/logout-all/``, a password change or a password reset remove the affected tokens from the
whitelist.

Every refresh token also carries a ``session_iat`` claim with the instant at which the session started.
Unlike ``iat``, it is copied unchanged into each rotated token, so it always points at the login that opened
the session. Setting ``JWT_ALLAUTH_SESSION_LIFETIME`` to a ``timedelta`` turns it into a hard deadline: once
``session_iat + JWT_ALLAUTH_SESSION_LIFETIME`` is reached the refresh endpoint deletes every whitelisted
token of that session and responds ``401`` with code ``session_expired``, and until then no refresh or access
token is issued with an expiration beyond that deadline.

Enable it when re-authentication has to happen on a schedule regardless of activity — a compliance
requirement such as NIST SP 800-63B, or to bound the exposure of a refresh token that leaked from a client
the legitimate user has stopped using, where token reuse never gets detected. Sessions started before the
limit was enabled have no ``session_iat``; their session start is anchored at their first rotation.

When ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` is ``True`` (default), refresh tokens are sent as secure HTTP-only cookies,
which provides enhanced security by making them inaccessible to JavaScript and reducing the risk of XSS attacks. When
set to ``False``, refresh tokens are included in the JSON response payload as they were traditionally handled.

Due to the stateless nature of JWT authentication, the user object in the request only contains the user ID. If you need
the complete user object in your view methods, you should use the :func:`~jwt_allauth.utils.load_user` decorator:

.. code-block:: python

    from jwt_allauth.utils import load_user

    class MyView(APIView):
        @load_user
        def get(self, request):
            # request.user is now the complete user object
            return Response({"username": request.user.username})
