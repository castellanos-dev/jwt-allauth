from django.contrib.auth import get_user_model
from django.test import override_settings

from .mixins import TestsMixin


class UserDetailsTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_user_details_unauthorized(self):
        resp = self.get(self.user_url, status_code=401)
        self.assertEqual(resp['detail'], u'Authentication credentials were not provided.')

    def test_user_details_methods_not_allowed(self):
        self.token = self.ACCESS

        resp = self.put(self.user_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.post(self.user_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "POST" not allowed.')
        resp = self.delete(self.user_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')

    def test_user_details(self):
        self.token = self.ACCESS

        resp = self.get(self.user_url, status_code=200)
        self.assertEqual(resp['email'], self.EMAIL)

    def test_user_details_patch(self):
        self.token = self.ACCESS

        resp = self.patch(self.user_url, data=self.BASIC_USER_DATA, status_code=200)
        user = get_user_model().objects.get(pk=self.USER.pk)
        self.assertEqual(user.first_name, self.BASIC_USER_DATA['first_name'])
        self.assertEqual(user.first_name, resp['first_name'])
        self.assertEqual(user.last_name, self.BASIC_USER_DATA['last_name'])
        self.assertEqual(user.last_name, resp['last_name'])
        self.assertEqual(user.email, resp['email'])

    def test_user_details_patch_with_extra_fields(self):
        self.token = self.ACCESS

        payload = {**self.BASIC_USER_DATA, 'dummy_field': 'dummy_value'}

        resp = self.patch(self.user_url, data=payload, status_code=200)
        user = get_user_model().objects.get(pk=self.USER.pk)
        self.assertEqual(user.first_name, self.USER_DATA['first_name'])
        self.assertEqual(user.first_name, resp['first_name'])
        self.assertEqual(user.last_name, self.USER_DATA['last_name'])
        self.assertEqual(user.last_name, resp['last_name'])
        self.assertEqual(user.email, resp['email'])
        self.assertFalse(hasattr(user, 'dummy_field'))
        self.assertNotIn('dummy_field', resp)

    def test_user_details_patch_one_filed(self):
        self.token = self.ACCESS

        payload = {'first_name': 'John'}

        resp = self.patch(self.user_url, data=payload, status_code=200)
        user = get_user_model().objects.get(pk=self.USER.pk)
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.first_name, resp['first_name'])
        self.assertEqual(user.last_name, resp['last_name'])
        self.assertEqual(user.email, resp['email'])

    def test_user_details_patch_with_empty_payload(self):
        self.token = self.ACCESS

        self.patch(self.user_url, data={}, status_code=200)

    def test_user_details_patch_read_only_email(self):
        self.token = self.ACCESS

        payload = {'email': 'dummy@email.com'}
        resp = self.patch(self.user_url, data=payload, status_code=200)
        user = get_user_model().objects.get(pk=self.USER.pk)
        self.assertEqual(user.email, self.EMAIL)
        self.assertEqual(user.email, resp['email'])

    def test_ja_user_model(self):
        self.token = self.ACCESS
        self.assertTrue(hasattr(self.USER, 'role'))
        role = self.USER.role

        resp = self.get(self.user_url, status_code=200)
        self.assertNotIn('role', resp)

        payload = {'role': 900}
        self.patch(self.user_url, data=payload, status_code=200)
        user = get_user_model().objects.get(pk=self.USER.pk)
        self.assertEqual(role, user.role)
        self.assertNotEqual(900, user.role)
