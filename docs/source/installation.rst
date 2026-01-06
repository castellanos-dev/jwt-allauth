Installation
------------

Quick Start
===========

Install using ``pip``...

.. code-block:: bash

    pip install django-jwt-allauth

You can quickly start a new Django project with JWT Allauth pre-configured using the ``startproject`` command:

.. code-block:: bash

    jwt-allauth startproject myproject

This will create a new Django project called "myproject" with JWT Allauth pre-configured. Then:

.. code-block:: bash

    cd myproject
    python manage.py migrate
    python manage.py runserver

Available options:

- ``--email=True`` - Enables email configuration in the project
- ``--template=PATH`` - Uses a custom template directory for project creation


Installation for existing projects
==================================

Install using ``pip``...

    pip install django-jwt-allauth

Add the following to your to your ``INSTALLED_APPS`` setting in the ``settings.py`` file **in the same order**:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'jwt_allauth',
        'rest_framework',
        'rest_framework.authtoken',
        'allauth',
        'allauth.account',
    ]

Set the ``AUTH_USER_MODEL`` setting in the ``settings.py`` file:

.. code-block:: python

    AUTH_USER_MODEL = 'jwt_allauth.JAUser'

If you want to use a custom user model, it **must inherit from** :class:`~jwt_allauth.models.JAUser`.
JWT Allauth expects fields and behavior provided by ``JAUser`` (notably the ``role`` field used in JWT claims and
permissions).
In that case, set ``AUTH_USER_MODEL`` to your model (for example ``users.CustomUser``) and run
``python manage.py makemigrations users`` before running ``migrate``.

Add the following to your ``MIDDLEWARE`` setting in the ``settings.py`` file:

.. code-block:: python

    MIDDLEWARE = [
        ...
        'allauth.account.middleware.AccountMiddleware',
    ]

Set the following to your ``AUTHENTICATION_BACKENDS`` setting in the ``settings.py`` file:

.. code-block:: python

    AUTHENTICATION_BACKENDS = (
        # Needed to login by username in Django admin, regardless of `allauth`
        "django.contrib.auth.backends.ModelBackend",
        # `allauth` specific authentication methods, such as login by e-mail
        "allauth.account.auth_backends.AuthenticationBackend"
    )

Add the following to your ``urls.py`` file.

.. code-block:: python

    from django.urls import path, include

    ...

    urlpatterns = [
        ...
        path('jwt-allauth/', include('jwt_allauth.urls')),
        ...
    ]

Run migrations.

.. code-block:: python

    python manage.py migrate

Done! ``django-jwt-allauth`` will configure ``django-allauth`` and ``djangorestframework-simplejwt`` for you.
