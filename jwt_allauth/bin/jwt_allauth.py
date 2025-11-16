#!/usr/bin/env python3
"""
JWT Allauth CLI tool for creating and managing projects
"""
import sys
import os
import argparse
import subprocess
import re


def main():
    """
    Main entry point for the JWT Allauth CLI
    """
    parser = argparse.ArgumentParser(
        description='JWT Allauth command line tool',
        usage='jwt-allauth <command> [options]'
    )
    parser.add_argument('command', help='Command to run (e.g. startproject)')

    # Parse just the command argument first
    args, remaining_args = parser.parse_known_args()

    if args.command == 'startproject':
        # Handle startproject command
        project_parser = argparse.ArgumentParser(
            description='Create a new Django project with JWT Allauth pre-configured',
            usage='jwt-allauth startproject <name> [directory] [options]'
        )
        project_parser.add_argument('name', help='Name of the project')
        project_parser.add_argument('directory', nargs='?', help='Optional directory to create the project in')
        project_parser.add_argument('--email', default='False', help='Email configuration (True/False)')
        project_parser.add_argument('--template', help='Template directory to use as a base')

        project_args = project_parser.parse_args(remaining_args)

        # Get project arguments
        project_name = project_args.name
        target_dir = project_args.directory or project_name
        email_config = project_args.email.lower() == 'true'
        template = project_args.template

        try:
            # Build command for running django-admin startproject
            cmd = ["django-admin", "startproject", project_name]

            # Add directory if specified
            if project_args.directory:
                cmd.append(project_args.directory)

            # Add template if specified
            if template:
                cmd.extend(["--template", template])

            # Run django-admin startproject
            print(f"Creating Django project '{project_name}'...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Error creating project: {result.stderr}")
                return 1

            print(f"✅ Created Django project '{project_name}'")

            # Step 2: Now modify the created project for JWT Allauth
            # Path to settings file
            settings_path = os.path.join(target_dir, project_name, 'settings.py')

            # Modify settings.py to include JWT-allauth configuration
            _modify_settings(settings_path, email_config)
            print("✅ Added JWT Allauth configuration to settings.py")

            # Add urls.py configuration
            urls_path = os.path.join(target_dir, project_name, 'urls.py')
            _modify_urls(urls_path)
            print("✅ Added JWT Allauth URLs to urls.py")

            # Create templates directory if needed
            if email_config:
                templates_dir = os.path.join(target_dir, 'templates')
                os.makedirs(templates_dir, exist_ok=True)
                print("✅ Created templates directory")

            # Final instructions
            print("\n✅ JWT Allauth project successfully created!")
            print("📋 Next steps:")
            print(f"   1. cd {target_dir}")
            print(f"   2. python manage.py makemigrations")
            print(f"   3. python manage.py migrate")
            print(f"   4. python manage.py runserver")

            if email_config:
                print("\n⚠️ Email configuration is enabled. Please update your email settings in settings.py")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Unexpected error: {str(e)}")
            return 1

    elif args.command == 'help':
        parser.print_help()
        print("\nAvailable commands:")
        print("  startproject  - Create a new Django project with JWT Allauth pre-configured")

    else:
        print(f"❓ Unknown command: {args.command}")
        parser.print_help()
        return 1

    return 0

def _modify_settings(settings_path, email_config):
    """Modify Django settings.py to include JWT Allauth configuration"""
    with open(settings_path, 'r') as f:
        settings_content = f.read()

    # Detect whether MFA support is available in the current environment.
    # We only configure MFA-related apps and settings when the optional
    # django-allauth[mfa] dependency is actually installed, to avoid
    # breaking generated projects.
    mfa_installed = False
    try:
        import allauth.mfa  # type: ignore  # noqa
        import allauth.mfa.totp  # type: ignore  # noqa
        import allauth.mfa.recovery_codes  # type: ignore  # noqa
        import jwt_allauth.mfa  # type: ignore  # noqa
    except Exception:  # pragma: no cover - purely defensive
        mfa_installed = False
    else:
        mfa_installed = True

    # Find INSTALLED_APPS content
    pattern = r"(INSTALLED_APPS\s*=\s*\[)(.*?)(,*\n*])"
    apps_lines = [
        "    'jwt_allauth',",
        "    'rest_framework',",
        "    'rest_framework.authtoken',",
        "    'allauth',",
        "    'allauth.account',",
        "    'allauth.socialaccount',",
    ]
    if mfa_installed:
        # Only add MFA-related apps when the optional allauth.mfa stack
        # is installed in the environment.
        apps_lines.append("    'allauth.mfa',")
    jwt_apps = "\n".join(apps_lines)

    # Replace keeping original Django apps and adding new ones before closing bracket
    settings_content = re.sub(pattern, fr'\1\2,\n{jwt_apps}\n]', settings_content, flags=re.DOTALL)

    # Add middleware
    pattern = r"(MIDDLEWARE\s*=\s*\[)(.*?)(,*\n*\])"
    allauth_middleware = "    'allauth.account.middleware.AccountMiddleware',"
    # Replace keeping original middleware and adding new one before closing bracket
    settings_content = re.sub(pattern, fr'\1\2,\n{allauth_middleware}\n]', settings_content, flags=re.DOTALL)

    # Add authentication backends
    auth_backends = """
# JWT Allauth user model
AUTH_USER_MODEL = 'jwt_allauth.JAUser'

# JWT Allauth adapter
ACCOUNT_ADAPTER = 'jwt_allauth.adapter.JWTAllAuthAdapter'

# Login configuration
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']

# Authentication backends
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend"
)

# Django Rest Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication',
    )
}

from datetime import timedelta

# JWT settings
JWT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)
JWT_REFRESH_TOKEN_LIFETIME = timedelta(days=90)
"""
    settings_content += auth_backends

    # Only add MFA-related settings when the optional MFA dependencies
    # are installed. This keeps generated projects working even if
    # django-allauth[mfa] is not present.
    if mfa_installed:
        mfa_settings = """

# MFA configuration
JWT_ALLAUTH_MFA_TOTP_MODE = 'optional'
JWT_ALLAUTH_TOTP_ISSUER = None

# Cache configuration (required for MFA)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
"""
        settings_content += mfa_settings

    # Add email configuration if requested
    if email_config:
        email_settings = """
# Email configuration
EMAIL_VERIFICATION = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.example.com'  # Update with your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'  # Update with your email
EMAIL_HOST_PASSWORD = 'your-password'  # Update with your password
DEFAULT_FROM_EMAIL = 'your-email@example.com'  # Update with your email

# JWT Allauth settings
EMAIL_VERIFIED_REDIRECT = None  # URL to redirect after email verification
PASSWORD_RESET_REDIRECT = None  # URL for password reset form
"""
        settings_content += email_settings

    with open(settings_path, 'w') as f:
        f.write(settings_content)

def _modify_urls(urls_path):
    """Modify Django urls.py to include JWT Allauth URLs"""
    with open(urls_path, 'r') as f:
        urls_content = f.read()

    no_comments_urls_content = re.sub(r'""".*?"""', '', urls_content, flags=re.DOTALL)

    # Add import for include if needed
    if "from django.urls import path" in no_comments_urls_content:
        if "include" not in no_comments_urls_content:
            urls_content = urls_content.replace(
                "from django.urls import path",
                "from django.urls import path, include"
            )
    elif "include" not in no_comments_urls_content:
        urls_content = "from django.urls import include\n" + urls_content

    # Add JWT-allauth URLs
    urls_pattern = r"(urlpatterns\s*=\s*\[)(.*?)(,*\n*\])"
    jwt_urls = "    path('jwt-allauth/', include('jwt_allauth.urls')),"
    urls_content = re.sub(urls_pattern, fr'\1\2,\n{jwt_urls}\n]', urls_content, flags=re.DOTALL)

    with open(urls_path, 'w') as f:
        f.write(urls_content)

if __name__ == '__main__':
    sys.exit(main())
