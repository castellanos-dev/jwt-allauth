import os
import sys
import shutil
from pathlib import Path
from django.core.management.commands.startproject import Command as StartProjectCommand
from django.core.management.base import CommandError
from django.template import Context, Engine


class Command(StartProjectCommand):
    help = 'Creates a new Django project with JWT Allauth pre-configured'

    def __init__(self, *args, **kwargs):
        print('entra1')
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        print('entra3')
        super().add_arguments(parser)
        print('entra4')
        parser.add_argument('--email', type=str, help='Email configuration (True/False)', default='False')

    def handle(self, *args, **options):
        project_name = options['name']
        target_dir = options.get('directory') or project_name
        email_config = options.get('email', 'False').lower() == 'true'
        
        print('entra')
        # First call the original startproject command
        super().handle(*args, **options)
        print('entra2')
        # Path to settings file
        settings_path = os.path.join(target_dir, project_name, 'settings.py')
        
        # Modify settings.py to include JWT-allauth configuration
        self._modify_settings(settings_path, email_config)
        self.stdout.write(self.style.SUCCESS("Added JWT Allauth configuration to settings.py"))
        
        # Add urls.py configuration
        urls_path = os.path.join(target_dir, project_name, 'urls.py')
        self._modify_urls(urls_path)
        self.stdout.write(self.style.SUCCESS("Added JWT Allauth URLs to urls.py"))
        
        # Create templates directory if needed
        if email_config:
            templates_dir = os.path.join(target_dir, 'templates')
            os.makedirs(templates_dir, exist_ok=True)
            self.stdout.write(self.style.SUCCESS("Created templates directory"))
        
        # Final instructions
        self.stdout.write("\n" + self.style.SUCCESS("JWT Allauth configuration completed successfully!"))
        
        if email_config:
            self.stdout.write(self.style.WARNING("\nEmail configuration is enabled. Please update your email settings in settings.py"))
    
    def _modify_settings(self, settings_path, email_config):
        with open(settings_path, 'r') as f:
            settings_content = f.read()
        
        # Add required apps
        apps_section = "INSTALLED_APPS = ["
        jwt_apps = """    'rest_framework',
    'rest_framework.authtoken',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'jwt_allauth',"""
        settings_content = settings_content.replace(apps_section, f"{apps_section}\n{jwt_apps}")
        
        # Add middleware
        middleware_section = "MIDDLEWARE = ["
        allauth_middleware = "    'allauth.account.middleware.AccountMiddleware',"
        # Insert middleware just before the closing bracket
        last_middleware_pos = settings_content.find("MIDDLEWARE = [")
        last_middleware_pos = settings_content.find("]", last_middleware_pos)
        settings_content = settings_content[:last_middleware_pos] + "\n" + allauth_middleware + settings_content[last_middleware_pos:]
        
        # Add authentication backends
        auth_backends = """
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
        'jwt_allauth.token.authentication.JWTAuthentication',
    )
}
"""
        settings_content += auth_backends
        
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
    
    def _modify_urls(self, urls_path):
        with open(urls_path, 'r') as f:
            urls_content = f.read()
        
        # Add import for include
        if "from django.urls import path" in urls_content and "include" not in urls_content:
            urls_content = urls_content.replace("from django.urls import path", "from django.urls import path, include")
        
        # Add JWT-allauth URLs
        urls_pattern = "urlpatterns = ["
        jwt_urls = "    path('jwt-allauth/', include('jwt_allauth.urls')),"
        urls_content = urls_content.replace(urls_pattern, f"{urls_pattern}\n{jwt_urls}")
        
        with open(urls_path, 'w') as f:
            f.write(urls_content) 