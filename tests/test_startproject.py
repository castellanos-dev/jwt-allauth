import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from jwt_allauth.bin.jwt_allauth import main, _modify_settings, _modify_urls


class TestStartProject(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.project_name = "testproject"
        self.project_dir = os.path.join(self.test_dir, self.project_name)

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_modify_settings(self):
        # Create a temporary settings file
        settings_path = os.path.join(self.test_dir, 'settings.py')
        with open(settings_path, 'w') as f:
            f.write("""
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
            """)

        # Modify settings
        _modify_settings(settings_path, email_config=True)

        # Read the modified settings
        with open(settings_path, 'r') as f:
            content = f.read()

        # Check if required apps are added
        self.assertIn("'rest_framework'", content)
        self.assertIn("'rest_framework.authtoken'", content)
        self.assertIn("'allauth'", content)
        self.assertIn("'allauth.account'", content)
        self.assertIn("'allauth.socialaccount'", content)
        self.assertIn("'jwt_allauth'", content)

        # Check if middleware is added
        self.assertIn("'allauth.account.middleware.AccountMiddleware'", content)

        # Check if authentication backends are added
        self.assertIn("AUTHENTICATION_BACKENDS", content)
        self.assertIn("django.contrib.auth.backends.ModelBackend", content)
        self.assertIn("allauth.account.auth_backends.AuthenticationBackend", content)

        # Check if REST framework settings are added
        self.assertIn("REST_FRAMEWORK", content)
        self.assertIn("rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication", content)

        # Check if email settings are added
        self.assertIn("EMAIL_VERIFICATION = True", content)
        self.assertIn("EMAIL_BACKEND", content)
        self.assertIn("EMAIL_HOST", content)
        self.assertIn("EMAIL_PORT", content)
        self.assertIn("EMAIL_USE_TLS", content)
        self.assertIn("EMAIL_HOST_USER", content)
        self.assertIn("EMAIL_HOST_PASSWORD", content)
        self.assertIn("DEFAULT_FROM_EMAIL", content)

    def test_modify_urls(self):
        # Create a temporary urls file
        urls_path = os.path.join(self.test_dir, 'urls.py')
        with open(urls_path, 'w') as f:
            f.write("""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]
            """)

        # Modify urls
        _modify_urls(urls_path)

        # Read the modified urls
        with open(urls_path, 'r') as f:
            content = f.read()

        # Check if include is added to imports
        self.assertIn("from django.urls import path, include", content)

        # Check if JWT Allauth URLs are added
        self.assertIn("path('jwt-allauth/', include('jwt_allauth.urls'))", content)

    @patch('subprocess.run')
    def test_startproject_command(self, mock_run):
        # Mock subprocess.run to simulate django-admin startproject
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        # Create a temporary directory for the project
        os.makedirs(os.path.join(self.project_dir, self.project_name), exist_ok=True)

        # Create settings.py and urls.py
        settings_path = os.path.join(self.project_dir, self.project_name, 'settings.py')
        urls_path = os.path.join(self.project_dir, self.project_name, 'urls.py')

        with open(settings_path, 'w') as f:
            f.write("INSTALLED_APPS = []\nMIDDLEWARE = []")

        with open(urls_path, 'w') as f:
            f.write("urlpatterns = []")

        # Run the command
        with patch('sys.argv', ['jwt-allauth', 'startproject', self.project_name, self.project_dir]):
            result = main()

        # Check if the command was successful
        self.assertEqual(result, 0)

        # Check if django-admin was called with correct arguments
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], 'django-admin')
        self.assertEqual(args[0][1], 'startproject')
        self.assertEqual(args[0][2], self.project_name)
        self.assertEqual(args[0][3], self.project_dir)

    @patch('subprocess.run')
    def test_startproject_with_email(self, mock_run):
        # Mock subprocess.run to simulate django-admin startproject
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        # Create a temporary directory for the project
        os.makedirs(os.path.join(self.project_dir, self.project_name), exist_ok=True)

        # Create settings.py and urls.py
        settings_path = os.path.join(self.project_dir, self.project_name, 'settings.py')
        urls_path = os.path.join(self.project_dir, self.project_name, 'urls.py')

        with open(settings_path, 'w') as f:
            f.write("INSTALLED_APPS = []\nMIDDLEWARE = []")

        with open(urls_path, 'w') as f:
            f.write("urlpatterns = []")

        # Run the command with email configuration
        with patch('sys.argv', ['jwt-allauth', 'startproject', self.project_name, self.project_dir, '--email', 'True']):
            result = main()

        # Check if the command was successful
        self.assertEqual(result, 0)

        # Check if templates directory was created
        templates_dir = os.path.join(self.project_dir, 'templates')
        self.assertTrue(os.path.exists(templates_dir))

        # Check if settings.py was modified with email configuration
        with open(settings_path, 'r') as f:
            content = f.read()
            self.assertIn("EMAIL_VERIFICATION = True", content)
            self.assertIn("EMAIL_BACKEND", content)

    @patch('subprocess.run')
    def test_startproject_error(self, mock_run):
        # Mock subprocess.run to simulate an error
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='Error creating project')

        # Run the command
        with patch('sys.argv', ['jwt-allauth', 'startproject', self.project_name]):
            result = main()

        # Check if the command failed
        self.assertEqual(result, 1)

        # Check if django-admin was called
        mock_run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
