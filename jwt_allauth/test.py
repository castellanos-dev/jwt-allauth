from allauth.account.internal.userkit import user_field
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.client import Client

from jwt_allauth.tokens.app_settings import RefreshToken


class JAClient(Client):
    """
    A custom Django test client for handling JWT authenticated requests.

    Provides enhanced HTTP methods to automatically include JWT tokens in requests.
    Supports both regular user and staff user authentication through separate tokens.

    All standard HTTP methods (post, get, patch, put, delete) are extended with:

        - Regular auth versions (auth_* methods) using default user token
        - Staff auth versions (staff_* methods) using staff user token
        - Optional direct token injection via access_token parameter

    """
    content_type = 'application/json'

    def __init__(self, token, staff_token, *args, **kwargs):
        self.ACCESS = token
        self.STAFF_ACCESS = staff_token
        super().__init__(*args, **kwargs)

    def update_kwargs(self, access_token=None, default_auth=False, staff_auth=False, **kwargs):
        kwargs['content_type'] = self.content_type
        if access_token is not None:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
        elif default_auth:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {self.ACCESS}'
        elif staff_auth:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {self.STAFF_ACCESS}'
        return kwargs

    def post(self, *args, access_token=None, **kwargs):
        kwargs = self.update_kwargs(access_token=access_token, **kwargs)
        return super().post(*args, **kwargs)

    def auth_post(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, default_auth=True)
        return super().post(*args, **kwargs)

    def get(self, *args, access_token=None, **kwargs):
        kwargs = self.update_kwargs(access_token=access_token, **kwargs)
        return super().get(*args, **kwargs)

    def auth_get(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, default_auth=True)
        return super().get(*args, **kwargs)

    def patch(self, *args, access_token=None, **kwargs):
        kwargs = self.update_kwargs(access_token=access_token, **kwargs)
        return super().patch(*args, **kwargs)

    def auth_patch(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, default_auth=True)
        return super().patch(*args, **kwargs)

    def put(self, *args, access_token=None, **kwargs):
        kwargs = self.update_kwargs(access_token=access_token, **kwargs)
        return super().put(*args, **kwargs)

    def auth_put(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, default_auth=True)
        return super().put(*args, **kwargs)

    def delete(self, *args, access_token=None, **kwargs):
        kwargs = self.update_kwargs(access_token=access_token, **kwargs)
        return super().delete(*args, **kwargs)

    def auth_delete(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, default_auth=True)
        return super().delete(*args, **kwargs)

    def staff_post(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, staff_auth=True)
        return super().post(*args, **kwargs)

    def staff_get(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, staff_auth=True)
        return super().get(*args, **kwargs)

    def staff_patch(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, staff_auth=True)
        return super().patch(*args, **kwargs)

    def staff_put(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, staff_auth=True)
        return super().put(*args, **kwargs)

    def staff_delete(self, *args, **kwargs):
        kwargs = self.update_kwargs(**kwargs, staff_auth=True)
        return super().delete(*args, **kwargs)


class JATestCase(TestCase):
    """
    Base test case for JWT-authenticated endpoint testing.

    Provides pre-configured user accounts and JWT tokens for testing:

        - Regular user with verified email
        - Staff user with verified email
        - Ready-to-use test client with authentication support
    """
    EMAIL = 'test@mail.com'
    PASS = 'Test-Passw0rd'
    FIRST_NAME = 'name'
    LAST_NAME = 'surname'
    USER = None
    LOGIN_PAYLOAD = {'email': EMAIL, 'password': PASS}
    STAFF_EMAIL = 'test@staff.com'
    STAFF_PASS = 'Staff-Passw0rd'
    STAFF_FIRST_NAME = 'staffname'
    STAFF_LAST_NAME = 'staffsurname'
    STAFF_USER = None

    def setUp(self):
        """
        Configures test environment with regular and staff users, including:

            - User account creation
            - Email verification setup
            - JWT token generation
        """
        self.USER = get_user_model().objects.create_user(self.EMAIL, email=self.EMAIL, password=self.PASS)
        user_field(self.USER, "first_name", self.FIRST_NAME)
        user_field(self.USER, "last_name", self.LAST_NAME)
        EmailAddress.objects.create(user=self.USER, email=self.EMAIL, verified=True, primary=True)
        self.TOKEN = RefreshToken().for_user(self.USER)
        self.ACCESS = str(self.TOKEN.access_token)
        self.USER.save()
        self.STAFF_USER = get_user_model().objects.create_user(
            self.STAFF_EMAIL, email=self.STAFF_EMAIL, password=self.STAFF_PASS, is_staff=True)
        user_field(self.STAFF_USER, "first_name", self.STAFF_FIRST_NAME)
        user_field(self.STAFF_USER, "last_name", self.STAFF_LAST_NAME)
        EmailAddress.objects.create(user=self.STAFF_USER, email=self.STAFF_EMAIL, verified=True, primary=True)
        self.STAFF_TOKEN = RefreshToken().for_user(self.STAFF_USER)
        self.STAFF_ACCESS = str(self.STAFF_TOKEN.access_token)
        self.STAFF_USER.save()

    @property
    def ja_client(self):
        """
        Pre-configured test client with authentication tokens.
        """
        return JAClient(self.ACCESS, self.STAFF_ACCESS)
