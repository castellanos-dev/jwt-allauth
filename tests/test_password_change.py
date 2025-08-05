from django.test import override_settings

from jwt_allauth.constants import REFRESH_TOKEN_COOKIE
from jwt_allauth.tokens.app_settings import RefreshToken
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from .mixins import TestsMixin


class PasswordChangeTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_password_change_unauthorized(self):
        resp = self.post(self.password_change_url, data={}, status_code=401)
        self.assertEqual(resp['detail'], u'Authentication credentials were not provided.')

    def test_password_wrong_token(self):
        self.token = 'dummy'
        resp = self.post(self.password_change_url, data={}, status_code=401)
        self.assertEqual(resp['detail'], u'Given token not valid for any token type')

    def test_password_change(self):
        self.token = self.ACCESS

        new_password_payload = {
            "old_password": self.PASS,
            "new_password1": "new_pass00",
            "new_password2": "new_pass00"
        }

        resp = self.post(self.password_change_url, data=new_password_payload, status_code=200)
        self.assertEqual(resp['detail'], u'New password has been saved.')

        # old password
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=401)
        self.assertEqual(resp['code'], u'incorrect_credentials')

        # new password
        login_payload = self.LOGIN_PAYLOAD.copy()
        login_payload['password'] = new_password_payload['new_password1']
        self.post(self.login_url, data=login_payload, status_code=200)

    def test_password_change_with_invalid_password(self):
        self.token = self.ACCESS

        new_password_payload = {
            "old_password": self.PASS,
            "new_password1": "new_person1",
            "new_password2": "new_person"
        }
        resp = self.post(
            self.password_change_url,
            data=new_password_payload,
            status_code=400
        )
        self.assertEqual(resp['new_password2'][0], u'The two password fields didn’t match.')

    def test_password_change_with_empty_payload(self):
        self.token = self.ACCESS
        # send empty payload
        resp = self.post(self.password_change_url, data={}, status_code=400)
        self.assertEqual(resp['old_password'][0], u'This field is required.')
        self.assertEqual(resp['new_password1'][0], u'This field is required.')
        self.assertEqual(resp['new_password2'][0], u'This field is required.')

    def test_password_change_with_wrong_old_password(self):
        self.token = self.ACCESS

        new_password_payload = {
            "old_password": 'wrong_password',
            "new_password1": "new_person",
            "new_password2": "new_person"
        }
        resp = self.post(
            self.password_change_url,
            data=new_password_payload,
            status_code=400
        )
        self.assertEqual(
            resp['old_password'][0], u'Your old password was entered incorrectly. Please enter it again.')

    def test_password_change_methods_not_allowed(self):
        self.token = self.ACCESS

        resp = self.get(self.password_change_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "GET" not allowed.')
        resp = self.put(self.password_change_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.patch(self.password_change_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PATCH" not allowed.')
        resp = self.delete(self.password_change_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')

    @override_settings(OLD_PASSWORD_FIELD_ENABLED=False)
    def test_password_change_without_old_password(self):
        self.token = self.ACCESS
        payload = {
            "new_password1": "new_pass00",
            "new_password2": "new_pass00"
        }
        self.post(self.password_change_url, data=payload, status_code=200)
        login_payload = self.LOGIN_PAYLOAD.copy()
        login_payload['password'] = payload['new_password1']
        self.post(self.login_url, data=login_payload, status_code=200)

    def test_password_validation_requirements(self):
        self.token = self.ACCESS
        payload = {
            "old_password": self.PASS,
            "new_password1": "short",
            "new_password2": "short"
        }
        resp = self.post(self.password_change_url, data=payload, status_code=400)
        self.assertIn("This password is too short.", str(resp))

    def test_refresh_jwt_tokens_invalidated_after_password_change(self):
        old_token = str(self.TOKEN)

        login_response = self.client.post(
            self.login_url,
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        self.token = login_data['access']
        current_token = login_response.cookies[REFRESH_TOKEN_COOKIE].value

        new_password_payload = {
            "old_password": self.PASS,
            "new_password1": "new_pass00",
            "new_password2": "new_pass00"
        }
        self.post(self.password_change_url, data=new_password_payload, status_code=200)

        # check other sessions - use override setting to test with payload
        with override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False):
            payload = {'refresh': old_token}
            resp = self.post(self.refresh_url, data=payload, status_code=401)
            self.assertEqual(resp['code'], u'token_not_valid')

        # check current session is alive - set cookie manually
        self.client.cookies[REFRESH_TOKEN_COOKIE] = current_token
        self.post(self.refresh_url, data={}, status_code=200)

    @override_settings(LOGOUT_ON_PASSWORD_CHANGE=False)
    def test_refresh_jwt_tokens_valid_after_password_change(self):
        old_token = str(self.TOKEN)

        login_response = self.client.post(
            self.login_url,
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        self.token = login_data['access']
        current_token = login_response.cookies[REFRESH_TOKEN_COOKIE].value

        new_password_payload = {
            "old_password": self.PASS,
            "new_password1": "new_pass00",
            "new_password2": "new_pass00"
        }
        self.post(self.password_change_url, data=new_password_payload, status_code=200)

        # check other sessions - use override setting to test with payload
        with override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False):
            payload = {'refresh': old_token}
            self.post(self.refresh_url, data=payload, status_code=200)

        # check current session is alive - set cookie manually
        self.client.cookies[REFRESH_TOKEN_COOKIE] = current_token
        self.post(self.refresh_url, data={}, status_code=200)

    def test_excessively_long_password(self):
        self.token = self.ACCESS
        long_pass = "a" * 129
        payload = {
            "old_password": self.PASS,
            "new_password1": long_pass,
            "new_password2": long_pass
        }
        resp = self.post(self.password_change_url, data=payload, status_code=400)
        self.assertIn("Ensure this field has no more than 128 characters.", resp['new_password1'])

    def test_sessions_revoked_password_change(self):
        self.token = self.ACCESS

        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()

        payload = {"old_password": self.PASS, "new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        self.post(self.password_change_url, data=payload, status_code=200)

        new_session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()
        self.assertTrue(new_session_count < session_count)

    @override_settings(LOGOUT_ON_PASSWORD_CHANGE=False)
    def test_sessions_not_revoked_password_change(self):
        self.token = self.ACCESS

        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        RefreshToken().for_user(self.USER)
        session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()

        payload = {"old_password": self.PASS, "new_password1": "P@sw0rd-set", "new_password2": "P@sw0rd-set"}
        self.post(self.password_change_url, data=payload, status_code=200)

        new_session_count = RefreshTokenWhitelistModel.objects.filter(user=self.USER).count()
        self.assertTrue(new_session_count >= session_count)
