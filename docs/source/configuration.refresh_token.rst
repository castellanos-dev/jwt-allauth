Refresh token
=============

Since this library is security and performance based, the authentication is performed in a completely stateless way,
which means the databased is not hit at every request to load the user information. The refresh token class can be
enhanced to incorporate additional data within its payload. This supplementary
information will automatically propagate to the access tokens during their generation. By embedding such data
directly in the tokens, this approach reduces reliance on frequent database queries, thereby alleviating server load.
Importantly, the refresh token whitelist mechanism ensures this strategy maintains robust security standards, as
compromised or outdated refresh tokens can be promptly invalidated when necessary.

Due to the stateless nature of JWT authentication, the user object in the request only contains the user ID. If you need
the complete user object in your view methods, you should use the :func:`~jwt_allauth.utils.load_user` decorator:

.. code-block:: python

    from jwt_allauth.utils import load_user

    class MyView(APIView):
        @load_user
        def get(self, request):
            # request.user is now the complete user object
            return Response({"username": request.user.username})

The following constant should be included in the settings.py file:

    - ``JWT_ALLAUTH_REFRESH_TOKEN`` - refresh token class (default: ``jwt_allauth.tokens.tokens.RefreshToken``).

Example:

.. code-block:: python

    from jwt_allauth.tokens.tokens import RefreshToken as DefaultRefreshToken

    class RefreshToken(DefaultRefreshToken):

        def set_user_permissions(self, user):
            self.payload['permissions'] = user.permissions

        @classmethod
        def for_user(cls, user, request=None, enabled=True):
            token = super().for_user(user)
            token.set_user_permissions(user)
            return token
