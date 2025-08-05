import json

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.test.client import Client, MULTIPART_CONTENT
from django.urls import reverse
from django.utils.encoding import force_str
from rest_framework import permissions
from rest_framework import status

from jwt_allauth.tokens.tokens import RefreshToken


class CustomPermissionClass(permissions.BasePermission):
    message = 'You shall not pass!'

    def has_permission(self, request, view):
        return False


class APIClient(Client):

    def patch(self, path, data='', content_type=MULTIPART_CONTENT, follow=False, **extra):
        return self.generic('PATCH', path, data, content_type, **extra)

    def options(self, path, data='', content_type=MULTIPART_CONTENT, follow=False, **extra):
        return self.generic('OPTIONS', path, data, content_type, **extra)


class TestsMixin(TransactionTestCase):
    """
    base for API tests:
        * easy request calls, f.e.: self.post(url, data), self.get(url)
        * easy status check, f.e.: self.post(url, data, status_code=200)
    """

    USERNAME = 'person'
    PASS = 'Val1dPasw0rd'
    EMAIL = "person1@world.com"
    NEW_PASS = 'new-test-pass'
    REGISTRATION_VIEW = 'jwt_allauth.runtests.RegistrationView'
    FIRST_NAME = 'John'
    LAST_NAME = 'Smith'

    LOGIN_PAYLOAD = {
        "email": EMAIL,
        "password": PASS
    }

    BASIC_USER_DATA = {
        'first_name': FIRST_NAME,
        'last_name': LAST_NAME,
        'email': EMAIL
    }
    USER_DATA = BASIC_USER_DATA.copy()
    USER_DATA['newsletter_subscribe'] = True

    def send_request(self, request_method, *args, **kwargs):
        request_func = getattr(self.client, request_method)
        status_code = None
        if 'content_type' not in kwargs and request_method != 'get':
            kwargs['content_type'] = 'application/json'
        if 'data' in kwargs and request_method != 'get' and kwargs['content_type'] == 'application/json':
            data = kwargs.get('data', '')
            kwargs['data'] = json.dumps(data)  # , cls=CustomJSONEncoder
        if 'status_code' in kwargs:
            status_code = kwargs.pop('status_code')

        # check_headers = kwargs.pop('check_headers', True)
        if hasattr(self, 'token'):
            kwargs['HTTP_AUTHORIZATION'] = 'Bearer %s' % self.token

        self.response = request_func(*args, **kwargs)
        if status_code:
            self.assertEqual(self.response.status_code, status_code)

        is_json = bool(
            [x for x in self.response.headers.values() if 'json' in x])

        self.response.json = {}
        if is_json and self.response.content:
            return json.loads(force_str(self.response.content))
        else:
            return self.response

    def post(self, *args, **kwargs):
        return self.send_request('post', *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.send_request('get', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.send_request('patch', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.send_request('put', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.send_request('delete', *args, **kwargs)

    def init(self):
        settings.DEBUG = True
        self.client = APIClient()

        self.login_url = reverse('rest_login')
        self.logout_url = reverse('rest_logout')
        self.logout_all_url = reverse('rest_logout_all')
        self.password_change_url = reverse('rest_password_change')
        self.register_url = reverse('rest_register')
        self.password_reset_url = reverse('rest_password_reset')
        self.user_url = reverse('rest_user_details')
        self.verify_email_url = reverse('account_confirm_email', args=['fake_key']).replace('fake_key/', '')
        self.refresh_url = reverse('token_refresh')
        # self.fb_login_url = reverse('fb_login')
        # self.tw_login_url = reverse('tw_login')
        # self.tw_login_no_view_url = reverse('tw_login_no_view')
        # self.tw_login_no_adapter_url = reverse('tw_login_no_adapter')
        # self.fb_connect_url = reverse('fb_connect')
        # self.tw_connect_url = reverse('tw_connect')
        # self.social_account_list_url = reverse('social_account_list')

        # user creation
        self.USER = get_user_model().objects.create_user(self.USERNAME, email=self.EMAIL, password=self.PASS)
        email = EmailAddress.objects.create(user=self.USER, email=self.EMAIL, verified=True, primary=True)

        self.TOKEN = RefreshToken().for_user(self.USER)
        self.ACCESS = str(self.TOKEN.access_token)

        self.USER.save()
        email.save()

    def _login(self):
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=status.HTTP_200_OK)
        self.assertIn('access', resp.keys())
        self.token = resp['access']

    def _logout(self):
        self.post(self.logout_all_url, status=status.HTTP_200_OK)
        del self.token

    @staticmethod
    def _generate_uid_and_token(user):
        result = {}
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode

        result['uid'] = urlsafe_base64_encode(force_bytes(user.pk))
        result['token'] = default_token_generator.make_token(user)
        return result
