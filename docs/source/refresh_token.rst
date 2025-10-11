Refresh token
=============

Since this library is security and performance based, the authentication is performed in a completely stateless way,
which means the databased is not hit at every request to load the user information. The refresh token class can be
enhanced to incorporate additional data within its payload. This supplementary
information will automatically propagate to the access tokens during their generation. Additional user attributes can be included via the ``JWT_ALLAUTH_USER_ATTRIBUTES`` setting. By embedding such data
directly in the tokens, this approach reduces reliance on frequent database queries, thereby alleviating server load.
Importantly, the refresh token whitelist mechanism ensures this strategy maintains robust security standards, as
compromised or outdated refresh tokens can be promptly invalidated when necessary.

The following constants should be included in the settings.py file:

    - ``JWT_ALLAUTH_REFRESH_TOKEN`` - refresh token class (default: ``jwt_allauth.tokens.tokens.RefreshToken``).

    - ``JWT_ALLAUTH_USER_ATTRIBUTES`` - dictionary mapping output claim names to user attribute paths to include in tokens (default: ``{}``). Example: ``{"organization_id": "organization.id", "area_id": "area.id"}``. The 'role' attribute is automatically included and should not be specified.

    - ``JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE`` - whether to send refresh tokens as HTTP-only cookies instead of in the JSON response payload (default: ``True``).

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
