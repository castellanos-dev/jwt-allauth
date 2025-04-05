#!/usr/bin/env python

import os

from setuptools import setup, find_namespace_packages

here = os.path.dirname(os.path.abspath(__file__))
f = open(os.path.join(here, 'README.md'))
long_description = f.read().strip()
f.close()


setup(
    name='django-jwt-allauth',
    version='1.0.0',
    author='Fernando Castellanos',
    author_email='fcastellanos.dev@gmail.com',
    url='http://github.com/castellanos-dev/django-jwt-allauth',
    description='Powerful JWT-allauth authentication for Django REST Framework that keeps the device session alive by renewing and whitelisting the refresh token.',  # noqa: E501
    packages=find_namespace_packages(
        exclude=["tests", "jwt_allauth.migrations"],
        include=["jwt_allauth", "jwt_allauth.*"]
    ),
    long_description=long_description,
    keywords='django rest auth registration rest-framework django-registration api allauth jwt whitelist',
    zip_safe=False,
    install_requires=[
        'Django>=4.2.16',
        'djangorestframework>=3.15.2',
        'six>=1.9.0',
        'django-allauth>=65.5.0',
        'djangorestframework-simplejwt>=5.3.1',
        'django-user-agents>=0.4.0',
    ],
    extras_require={
        "test": ["responses>=0.5.0"]
    },
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
    include_package_data=True,
    package_data={
        "jwt_allauth": [
            "templates/**/*.html",
            "templates/**/*.txt",
            "locale/**/*.po",
        ],
    },
    entry_points={
        'console_scripts': [
            'jwt-allauth=jwt_allauth.bin.jwt_allauth:main',
        ],
    },
)
