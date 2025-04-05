API endpoints
=============

Authentication
--------------

- **/login/** (POST)

    - email
    - password

  Returns: access, refresh

  Reverse name: rest_login

.. note:: Django Rest Framework throttling enabled, see: https://www.django-rest-framework.org/api-guide/throttling/

- **/refresh/** (POST)

    - refresh

  Returns: access, refresh

  Reverse name: token_refresh

- **/logout/** (POST) ``[Authenticated]``

    - refresh

  Reverse name: rest_logout

- **/logout-all/** (POST)

- **/password/reset/** (POST) ``[Authenticated]``

    - email

  Returns: access, refresh

  Reverse name: rest_password_reset

.. note:: Django Rest Framework throttling enabled, see: https://www.django-rest-framework.org/api-guide/throttling/

.. warning:: Requires a email server configured.

- **/password/reset/confirm/<str:uidb64>/<str:token>/** (GET)

  Reverse name: password_reset_confirm

.. note:: uid and token are sent in email after calling /rest-auth/password/reset/

- **/password/reset/default/** (GET)

  Reverse name: default_password_reset

.. note:: Default password reset form. Used when PASSWORD_RESET_REDIRECT is not configured.

- **/password/reset/complete/** (GET)

  Reverse name: jwt_allauth_password_reset_complete

.. note:: Used when PASSWORD_RESET_REDIRECT is not configured.

- **/password/reset/set-new/** (POST) ``[Cookie]``

    - new_password1
    - new_password2

  Reverse name: password_reset_confirm

- **/password/change/** (POST) ``[Authenticated]``

    - new_password1
    - new_password2
    - old_password

  Reverse name: rest_password_change

.. note:: ``OLD_PASSWORD_FIELD_ENABLED = True`` to use old_password (default).
.. note:: ``LOGOUT_ON_PASSWORD_CHANGE = True`` to logout from the remaining sessions.

- **/user/** (GET, PUT, PATCH) ``[Authenticated]``

    - email
    - first_name
    - last_name

  Returns: email, first_name, last_name

  Reverse name: rest_user_details

Registration
------------

- **/registration/** (POST)

    - password1
    - password2
    - email
    - first_name
    - last_name

  Reverse name: rest_register

- **/registration/verification/<str:key>/** (GET)

.. note:: Disabled when ``EMAIL_VERIFICATION = False``.

  Reverse name: account_confirm_email

- **/registration/account_email_verification_sent/** (GET)

  Reverse name: account_email_verification_sent

.. note:: Disabled when ``EMAIL_VERIFICATION = False``.

- **/registration/verified/** (GET)

  Reverse name: jwt_allauth_email_verified

.. note:: Disabled if ``EMAIL_VERIFIED_REDIRECT`` is defined or ``EMAIL_VERIFICATION = False``.
