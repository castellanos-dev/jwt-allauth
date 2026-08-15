Installation
------------

Supported versions
==================

Python 3.10+ and Django 4.2+, on any Django REST Framework 3.15+. The combinations the
suite runs against are the floor (Django 4.2, allauth 65.9, Simple JWT 5.3.1), the
current Django LTS, and whatever is newest on the day CI runs.

The dependencies carry **no upper bounds**: a cap in a library propagates a conflict to
every project that depends on it and blocks the capped package's security releases.

What takes their place is a startup check. jwt-allauth builds on internals of allauth and
Simple JWT -- Simple JWT's token and authentication classes are subclassed and its
settings rewritten at startup, and allauth's TOTP and recovery-code helpers live under a
package named ``internal`` -- so a new major of either can move ground this library
stands on. When one is newer than anything the release was tested against,
``manage.py check`` says so (``jwt_allauth.W003``) and names what to exercise before
deploying. It is a heads-up, not a fault, and

.. code-block:: python

    SILENCED_SYSTEM_CHECKS = ['jwt_allauth.W003']

turns it off.

Quick Start
===========

Install using ``pip``...

.. code-block:: bash

    pip install django-jwt-allauth

Three features ship behind extras and are not installed by that command; see
:ref:`optional-features`.

You can quickly start a new Django project with JWT Allauth pre-configured using the ``startproject`` command:

.. code-block:: bash

    jwt-allauth startproject myproject

This will create a new Django project called "myproject" with JWT Allauth pre-configured. Then:

.. code-block:: bash

    cd myproject
    python manage.py makemigrations jwt_allauth
    python manage.py migrate
    python manage.py runserver

Projects created via ``jwt-allauth startproject`` are configured to store ``jwt_allauth`` migrations inside your project codebase via Django's ``MIGRATION_MODULES`` setting. This is especially useful in Docker environments where your project source code is persisted (and committed to git) but ``site-packages`` is ephemeral.

The generated migration files will live under:

.. code-block:: text

    myproject/
        myproject/
            migrations_external/
                jwt_allauth/
                    0001_initial.py
                    ...

Available options:

- ``--email=True`` - Enables email configuration in the project
- ``--template=PATH`` - Uses a custom template directory for project creation


.. _optional-features:

Optional features
=================

Three features ship behind extras, so that a project only carries the dependencies of what
it actually uses. Each is installed from this package; nothing has to be installed from
``django-allauth`` by hand.

.. list-table::
   :widths: 15 42 43
   :header-rows: 1

   * - Extra
     - Install
     - What it adds
   * - ``mfa``
     - ``pip install "django-jwt-allauth[mfa]"``
     - TOTP second factor with recovery codes. See :doc:`mfa_totp`.
   * - ``social``
     - ``pip install "django-jwt-allauth[social]"``
     - Sign-in through an identity provider. See :doc:`social_login`.
   * - ``schema``
     - ``pip install "django-jwt-allauth[schema]"``
     - OpenAPI annotations through drf-spectacular. See :doc:`api_endpoints`.

They combine: ``pip install "django-jwt-allauth[mfa,social]"``.


Languages
=========

Every message the library returns — the errors, the notices, and the e-mails it sends —
is translated into Czech, German, Spanish, French, Korean, Polish, Brazilian Portuguese,
Russian, Turkish and Chinese (Simplified and Traditional). Compiled catalogues ship in
the package, so nothing has to be built after installing.

Django decides which one is used, and it needs two things beyond the defaults:

.. code-block:: python

    USE_I18N = True                 # on by default
    LANGUAGE_CODE = 'es'            # the fallback when no language is negotiated

    MIDDLEWARE = [
        # ...
        'django.middleware.locale.LocaleMiddleware',   # honours Accept-Language per request
        # ...
    ]

Without ``LocaleMiddleware`` every response comes back in ``LANGUAGE_CODE``, which is
what an API serving one locale wants. With it, each request is answered in the language
its ``Accept-Language`` header asks for, falling back to ``LANGUAGE_CODE``.

The error ``code`` beside each ``detail`` is never translated — it is what a client
branches on, and ``detail`` is what a person reads.

A language that is missing, or a phrasing that is wrong for your users: the source
catalogues are in ``jwt_allauth/locale/<code>/LC_MESSAGES/django.po`` and pull requests
are welcome. See ``CONTRIBUTING.md`` for the two commands involved.


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

To make migrations persistent across environments (recommended for Docker), configure local migration modules for ``jwt_allauth`` using ``MIGRATION_MODULES``.

1) Create the local migrations package inside your Django project module (replace ``myproject`` with your project module name):

.. code-block:: text

    myproject/
        myproject/
            migrations_external/
                __init__.py
                jwt_allauth/
                    __init__.py

2) Add this to your ``settings.py``:

.. code-block:: python

    MIGRATION_MODULES = {
        'jwt_allauth': 'myproject.migrations_external.jwt_allauth',
    }

3) Generate and apply migrations:

.. code-block:: bash

    python manage.py makemigrations jwt_allauth
    python manage.py migrate

Done! ``django-jwt-allauth`` will configure ``django-allauth`` and ``djangorestframework-simplejwt`` for you.

Maintenance
===========

Tokens are stored while they can still be used and removed when they are used: the single-use ones — password
reset and password set links, the capabilities they are exchanged for, email confirmations and the MFA
challenges — and the whitelisted refresh tokens behind the sessions. Nothing removes the ones nobody comes back
for: an unopened reset link, an invitation nobody accepts, a session left on a device that never logs out. So
schedule:

.. code-block:: bash

    python manage.py jwt_allauth_purge_tokens

It deletes only what is past the lifetime of the flow that issued it — an expired refresh token is rejected on
its own ``exp`` before the whitelist is read, and every other flow checks its own expiry too — so nothing that
could still be honoured is removed. It also reports the purposes it left alone because no retention is
configured for them (see ``JWT_ALLAUTH_TOKEN_RETENTION``). Add ``--dry-run`` to count without deleting.
