Serializers
===========

You can define your custom serializers for each endpoint without overriding urls and views by adding ``JWT_ALLAUTH_SERIALIZERS`` dictionary in your django settings.
Possible key values:

    - ``LOGIN_SERIALIZER`` - serializer class in :class:`~jwt_allauth.login.views.LoginView`, default value :class:`~jwt_allauth.login.serializers.LoginSerializer`

    - ``REGISTER_SERIALIZER`` - serializer class in :class:`~jwt_allauth.registration.views.RegisterView`, default value :class:`~jwt_allauth.registration.serializers.RegisterSerializer`

    - ``USER_DETAILS_SERIALIZER`` - serializer class in :class:`~jwt_allauth.user_details.views.UserDetailsView`, default value :class:`~jwt_allauth.user_details.serializers.UserDetailsSerializer`

    - ``PASSWORD_RESET_SERIALIZER`` - serializer class in :class:`~jwt_allauth.password_reset.views.PasswordResetView`, default value :class:`~jwt_allauth.password_reset.serializers.PasswordResetSerializer`

    - ``PASSWORD_CHANGE_SERIALIZER`` - serializer class in :class:`~jwt_allauth.password_change.views.PasswordChangeView`, default value :class:`~jwt_allauth.password_change.serializers.PasswordChangeSerializer`


Example configuration:

.. code-block:: python

    JWT_ALLAUTH_SERIALIZERS = {
        'LOGIN_SERIALIZER': 'path.to.custom.LoginSerializer',
        'TOKEN_SERIALIZER': 'path.to.custom.TokenSerializer',
        ...
    }
