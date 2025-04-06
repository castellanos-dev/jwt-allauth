from .mixins import TestsMixin


class LoginTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_login_failed_empty_email_validation(self):
        payload = {
            "email": '',
            "password": self.PASS
        }

        resp = self.post(self.login_url, data=payload, status_code=400)
        self.assertEqual(resp['email'][0], u'This field may not be blank.')

    def test_login_failed_empty_password_validation(self):
        payload = {
            "email": self.EMAIL,
            "password": '',
        }

        resp = self.post(self.login_url, data=payload, status_code=400)
        self.assertEqual(resp['password'][0], u'This field may not be blank.')

    def test_login_failed_empty_password_and_empty_email_validation(self):
        payload = {
            "email": '',
            "password": '',
        }

        resp = self.post(self.login_url, data=payload, status_code=400)
        self.assertEqual(resp['email'][0], u'This field may not be blank.')
        self.assertEqual(resp['password'][0], u'This field may not be blank.')

    def test_login_failed_no_email_validation(self):
        payload = {
            "password": self.PASS
        }

        resp = self.post(self.login_url, data=payload, status_code=400)
        self.assertEqual(resp['email'][0], u'This field is required.')

    def test_login_failed_no_password_validation(self):
        payload = {
            "email": self.EMAIL
        }

        resp = self.post(self.login_url, data=payload, status_code=400)
        self.assertEqual(resp['password'][0], u'This field is required.')

    def test_login_no_payload(self):
        resp = self.post(self.login_url, data={}, status_code=400)
        self.assertEqual(resp['email'][0], u'This field is required.')
        self.assertEqual(resp['password'][0], u'This field is required.')

    def test_login_non_existing_user(self):
        payload = {
            "email": 'dummy@email.com',
            "password": 'password'
        }

        resp = self.post(self.login_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], u'incorrect_credentials')

    def test_login_incorrect_password(self):
        payload = {
            "email": self.EMAIL,
            "password": 'WrongPassword'
        }

        resp = self.post(self.login_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], u'incorrect_credentials')

    def test_correct_login_with_email(self):
        json_resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)
        self.assertIn('refresh', json_resp.keys())
        self.assertIn('access', json_resp.keys())

        # test authenticated API with no token
        resp = self.get(self.user_url, status_code=401)
        self.assertEqual(resp['detail'], u'Authentication credentials were not provided.')

        # set login token
        self.token = json_resp['access']
        # test authenticated API with token
        self.get(self.user_url, status_code=200)

    def test_correct_login_upper_case_email(self):
        # test uppercase email
        payload = {
            "email": self.EMAIL.upper(),
            "password": self.PASS
        }
        self.post(self.login_url, data=payload, status_code=200)

    def test_login_inactive_user(self):
        self.USER.is_active = False
        self.USER.save()
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=401)
        self.assertEqual(resp['detail'], u'No active account found with the given credentials')

    def test_login_not_allowed_methods(self):
        resp = self.get(self.login_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "GET" not allowed.')
        resp = self.put(self.login_url, data=self.LOGIN_PAYLOAD, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.patch(self.login_url, data=self.LOGIN_PAYLOAD, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PATCH" not allowed.')
        resp = self.delete(self.login_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')

    def test_login_email_with_whitespace(self):
        payload = {
            "email": f"  {self.EMAIL}  ",
            "password": self.PASS
        }
        json_resp = self.post(self.login_url, data=payload, status_code=200)
        self.assertIn('access', json_resp)

    def test_password_not_in_login_response(self):
        json_resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)
        self.assertNotIn('password', json_resp)

    def test_login_response_content_type(self):
        response = self.client.post(
            self.login_url,
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(response['Content-Type'], 'application/json')
