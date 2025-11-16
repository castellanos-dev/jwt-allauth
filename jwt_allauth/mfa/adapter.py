"""
Custom MFA Adapter for JWT All-Auth.

This module provides a customized MFA adapter that inherits from allauth's
DefaultMFAAdapter, allowing override of specific MFA behavior such as the
TOTP issuer configuration.
"""

from django.conf import settings

from allauth.mfa.adapter import DefaultMFAAdapter


class JWTAllAuthMFAAdapter(DefaultMFAAdapter):
    """
    Custom MFA adapter extending allauth's DefaultMFAAdapter with JWT-specific MFA handling.

    This adapter allows customization of MFA behavior for JWT authentication scenarios,
    specifically enabling the use of a custom TOTP issuer name configured via
    JWT_ALLAUTH_TOTP_ISSUER setting instead of the default allauth TOTP_ISSUER.

    Key Features:

        - Custom TOTP issuer configuration via JWT_ALLAUTH_TOTP_ISSUER setting
        - Fallback to site name if no custom issuer is configured
        - Full compatibility with allauth MFA functionality
        - Seamless integration with JWT authentication workflows

    Configuration:

        The adapter is automatically configured when jwt_allauth is installed in INSTALLED_APPS.

        To customize the TOTP issuer, set the following in your Django settings:

            JWT_ALLAUTH_TOTP_ISSUER = "Your App Name"

        Priority order for TOTP issuer:

            1. JWT_ALLAUTH_TOTP_ISSUER (if set)
            2. 'JWT-Allauth' (default if setting is not provided)
            3. Current site name (if JWT_ALLAUTH_TOTP_ISSUER is explicitly set to None or empty)

    Example:

        settings.py::

            INSTALLED_APPS = [
                ...
                'allauth',
                'allauth.account',
                'allauth.mfa',
                'jwt_allauth',
                ...
            ]

            # Optional: customize the TOTP issuer name
            JWT_ALLAUTH_TOTP_ISSUER = "My App"
    """

    def get_totp_issuer(self) -> str:
        """
        Return the TOTP issuer name that will be contained in the TOTP QR code.

        This method overrides the parent implementation to check for JWT_ALLAUTH_TOTP_ISSUER
        in Django settings with a default fallback.

        Priority order:

            1. JWT_ALLAUTH_TOTP_ISSUER (if provided in settings)
            2. 'JWT-Allauth' (default value)
            3. Current site name (only if JWT_ALLAUTH_TOTP_ISSUER is explicitly empty/None)

        Returns:
            str: The TOTP issuer name to be used in QR code generation.
                 Typically the application or organization name.

        Example:

            With default configuration (no JWT_ALLAUTH_TOTP_ISSUER set)::

                >>> adapter = JWTAllAuthMFAAdapter()
                >>> issuer = adapter.get_totp_issuer()
                >>> print(issuer)
                'JWT-Allauth'

            With custom JWT_ALLAUTH_TOTP_ISSUER::

                # settings.py: JWT_ALLAUTH_TOTP_ISSUER = "My App"
                >>> adapter = JWTAllAuthMFAAdapter()
                >>> issuer = adapter.get_totp_issuer()
                >>> print(issuer)
                'My App'
        """
        # Check for JWT_ALLAUTH_TOTP_ISSUER with 'JWT-Allauth' as default
        issuer = getattr(settings, "JWT_ALLAUTH_TOTP_ISSUER", 'JWT-Allauth')
        if not issuer:
            issuer = self._get_site_name()
        return issuer
