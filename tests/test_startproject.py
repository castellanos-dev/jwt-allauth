import os
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase, override_settings
from jwt_allauth.bin.jwt_allauth import main, _generate_rsa_keys, _modify_settings, _modify_urls


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
        _modify_settings(settings_path, email_config=True, project_module='testproject')

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

        # Social authentication is offered but left switched off: a commented provider
        # block, and no live setting for a project that does not want it.
        self.assertIn("# SOCIALACCOUNT_PROVIDERS = {", content)
        self.assertIn("# JWT_ALLAUTH_SOCIAL_EMAIL_LINKING = True", content)
        self.assertNotIn("\nSOCIALACCOUNT_PROVIDERS", content)

        # Invitations are offered the same way, in the same block.
        self.assertIn("# JWT_ALLAUTH_INVITATIONS = True", content)
        self.assertIn("# PASSWORD_SET_REDIRECT = ", content)
        self.assertNotIn("\nJWT_ALLAUTH_INVITATIONS", content)

        # Check if authentication backends are added
        self.assertIn("AUTHENTICATION_BACKENDS", content)
        self.assertIn("django.contrib.auth.backends.ModelBackend", content)
        self.assertIn("allauth.account.auth_backends.AuthenticationBackend", content)

        # Check if REST framework settings are added
        self.assertIn("REST_FRAMEWORK", content)
        self.assertIn("jwt_allauth.authentication.JWTAllAuthAuthentication", content)

        # Check if email settings are added
        self.assertIn("EMAIL_VERIFICATION = True", content)
        self.assertIn("EMAIL_BACKEND", content)
        self.assertIn("EMAIL_HOST", content)
        self.assertIn("EMAIL_PORT", content)
        self.assertIn("EMAIL_USE_TLS", content)
        self.assertIn("EMAIL_HOST_USER", content)
        self.assertIn("EMAIL_HOST_PASSWORD", content)
        self.assertIn("DEFAULT_FROM_EMAIL", content)

        # Check if migration modules are configured
        self.assertIn("MIGRATION_MODULES", content)
        self.assertIn("testproject.migrations_external.jwt_allauth", content)

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

        # Check if local migration modules were created
        migrations_dir = os.path.join(self.project_dir, self.project_name, 'migrations_external', 'jwt_allauth')
        self.assertTrue(os.path.exists(migrations_dir))

        # Check if settings.py includes MIGRATION_MODULES configuration
        with open(settings_path, 'r') as f:
            content = f.read()
            self.assertIn("MIGRATION_MODULES", content)
            self.assertIn("testproject.migrations_external.jwt_allauth", content)

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

        # Check if local migration modules were created
        migrations_dir = os.path.join(self.project_dir, self.project_name, 'migrations_external', 'jwt_allauth')
        self.assertTrue(os.path.exists(migrations_dir))

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


class GeneratedProjectChecksTests(SimpleTestCase):
    """
    A generated project must boot clean.

    `startproject` writes 'allauth.socialaccount' into INSTALLED_APPS, and for a while
    that alone was enough to make `manage.py check` tell every new project to go and
    configure Google for a feature it had not asked for. Any project generated by an
    earlier release inherited the same warning on upgrade, and a CI running
    `check --fail-level WARNING` broke on it.
    """

    def test_social_check_is_silent_for_the_generated_configuration(self):
        from jwt_allauth.checks import check_social_providers

        generated_apps = [
            'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
            'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
            'jwt_allauth', 'rest_framework', 'rest_framework.authtoken',
            'allauth', 'allauth.account', 'allauth.socialaccount',
        ]
        with override_settings(INSTALLED_APPS=generated_apps, SOCIALACCOUNT_PROVIDERS={}):
            self.assertEqual(check_social_providers(None), [])


class TestSigningKeyPermissions(unittest.TestCase):
    """
    The generated signing key is not readable by anybody but its owner.

    It signs every access token the project issues, and this library authenticates
    statelessly by default -- a token minted with a stolen key is accepted without a
    single query. A key left at the process umask (0644 on most hosts) hands that to any
    local user, and to anything that archives the working directory.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.keys_dir = os.path.join(self.test_dir, 'keys')

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @unittest.skipIf(os.name != 'posix', 'POSIX permission bits')
    def test_private_key_is_not_readable_by_others(self):
        # A permissive umask is the case that matters: the default on many hosts, and
        # the one that used to decide the key's mode.
        previous = os.umask(0o000)
        try:
            self.assertTrue(_generate_rsa_keys(self.keys_dir))
        finally:
            os.umask(previous)

        private = os.path.join(self.keys_dir, 'private.pem')
        self.assertEqual(stat.S_IMODE(os.stat(private).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.keys_dir).st_mode), 0o700)

    @unittest.skipIf(os.name != 'posix', 'POSIX permission bits')
    def test_an_existing_keys_directory_is_narrowed_too(self):
        """``makedirs`` does nothing to a directory that already exists."""
        os.makedirs(self.keys_dir)
        os.chmod(self.keys_dir, 0o755)

        self.assertTrue(_generate_rsa_keys(self.keys_dir))

        self.assertEqual(stat.S_IMODE(os.stat(self.keys_dir).st_mode), 0o700)

    def test_the_keys_are_kept_out_of_version_control(self):
        self.assertTrue(_generate_rsa_keys(self.keys_dir))

        with open(os.path.join(self.keys_dir, '.gitignore')) as f:
            self.assertIn('*.pem', f.read())
