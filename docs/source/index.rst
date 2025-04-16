.. JWT Allauth documentation master file, created by
   sphinx-quickstart on Mon Mar 10 20:15:01 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to JWT Allauth
======================

JWT Allauth delivers **SIMPLE** authentication for the Django REST module, based on robust frameworks configured in 
an **efficient** and stateless way through **JWT** access/refresh token architecture. The token whitelisting system 
ensures granular control over user sessions while maintaining minimal database overhead.

With **JWT Allauth**, gain peace of mind through enterprise-grade security while dedicating your energy to building 
your app's unique value proposition.


Features
--------

- **Low database load**: Designed to minimize database queries through stateless JWT token authentication.
- Token whitelisting system: Implements a refresh token whitelist tied to specific device sessions.
- **Enhanced security**: Enables revoking access to specific devices or all devices simultaneously.
- Automatic token renewal: Active sessions for extended periods without reauthentication, ideal for **mobile apps**.
- Email verification: Includes a full **REST email verification** system during user registration.
- Comprehensive user management: Features password recovery, email-based authentication, and session logout.
- **Effortless setup**: Get your project up and running with a single command.


Why whitelisting?
-----------------

The refresh token whitelist tracks devices **authorized by the user**, stored in the database to verify refresh tokens
during access token renewal requests.

This system empowers users to **revoke access** to stolen/lost devices or log out of all sessions simultaneously. 
Refresh tokens are regenerated upon each use, ensuring active session tracking. If a refresh token is reused, the 
system invalidates both tokens and terminates the session tied to the compromised device.

Refresh token auto-renewal enables extended active sessions without repeated logins—ideal for **mobile apps**, where 
users shouldn't need to reauthenticate every time they open the app.

Access tokens provide short-lived authentication credentials (via JWT), enabling stateless API access. This 
approach **minimizes database load** by eliminating per-request database queries.


Quick Start
-----------

Install using ``pip``...

.. code-block:: bash

    pip install django-jwt-allauth

You can quickly start a new Django project with JWT Allauth pre-configured using the ``startproject`` command:

.. code-block:: bash

    jwt-allauth startproject myproject

This will create a new Django project called "myproject" with JWT Allauth pre-configured. Then:

.. code-block:: bash

    cd myproject
    python manage.py makemigrations
    python manage.py migrate
    python manage.py runserver

Available options:

- ``--email=True`` - Enables email configuration in the project
- ``--template=PATH`` - Uses a custom template directory for project creation


Source Code
-----------

The source code is available at `GitHub <https://github.com/castellanos-dev/jwt-allauth>`_.


Contents
--------
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
   release_notes

Acknowledgements
----------------
This project began as a fork of django-rest-auth. Thanks to the authors for their great work.
