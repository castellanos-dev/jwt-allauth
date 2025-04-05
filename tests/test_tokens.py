import time
from datetime import datetime, timedelta

from allauth.account.models import EmailAddress
from django.test import override_settings

from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.tokens import RefreshToken
from .mixins import TestsMixin



class TokenTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_refresh_no_payload(self):

        resp = self.post(self.refresh_url, data={}, status_code=400)
        self.assertIn(resp['refresh'][0], u'This field is required.')

    def test_refresh_invalid_payload(self):
        payload = {'refresh': 'dummy_refresh'}

        resp = self.post(self.refresh_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], u'token_not_valid')

    def test_refresh(self):
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(
            jti=self.TOKEN.payload['jti']
        ).filter(session=self.TOKEN.payload['session']).exists())

        payload = {'refresh': str(self.TOKEN)}

        time.sleep(1)  # wait for 1 second to make sure the new expiration is different
        resp = self.post(self.refresh_url, data=payload, status_code=200)
        self.assertTrue('access' in resp.keys())
        self.assertTrue('refresh' in resp.keys())
        new_token = RefreshToken(resp['refresh'])

        self.assertNotEqual(self.TOKEN.payload['jti'], new_token.payload['jti'])
        self.assertEqual(self.TOKEN.payload['session'], new_token.payload['session'])
        self.assertTrue(self.TOKEN.payload['exp'] < new_token.payload['exp'])
        self.assertTrue(self.TOKEN.payload['iat'] < new_token.payload['iat'])

        self.assertTrue(not RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti']).exists())
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(jti=new_token.payload['jti']).exists())
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(session=new_token.payload['session']).exists())

        # user agent
        self.assertEqual(
            RefreshTokenWhitelistModel.objects.filter(jti=new_token.payload['jti']).all()[0].ip, '127.0.0.1')
        self.assertEqual(
            RefreshTokenWhitelistModel.objects.filter(jti=new_token.payload['jti']).all()[0].browser, 'Other')
        self.assertTrue(
            RefreshTokenWhitelistModel.objects.filter(jti=new_token.payload['jti']).all()[0].created.timestamp() -
            datetime.now().timestamp() < 100
        )

        # suspicious activity (token refresh reused)
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())
        resp = self.post(self.refresh_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], u'token_not_valid')
        self.assertTrue(not RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())

    def test_refresh_token_disabled(self):
        token_object = RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti'])[0]
        token_object.enabled = False
        token_object.save()

        payload = {'refresh': str(self.TOKEN)}

        resp = self.post(self.refresh_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], u'token_not_valid')

    def test_refresh_not_verified_email(self):
        EmailAddress.objects.filter(user=self.USER).delete()
        token_object = RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti'])[0]
        token_object.enabled = False
        token_object.save()

        payload = {'refresh': str(self.TOKEN)}

        resp = self.post(self.refresh_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], u'email_not_verified')

    def test_refresh_not_whitelisted(self):
        RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti']).delete()

        payload = {'refresh': str(self.TOKEN)}

        resp = self.post(self.refresh_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], u'token_not_valid')

    def test_refresh_methods_not_allowed(self):
        resp = self.get(self.refresh_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "GET" not allowed.')
        resp = self.put(self.refresh_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.patch(self.refresh_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PATCH" not allowed.')
        resp = self.delete(self.refresh_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')

    def test_xss_injection_in_device_fields(self):
        malicious_payload = {
            'refresh': str(self.TOKEN),
            'browser': '<script>alert("XSS")</script>',
            'ip': '127.0.0.1; DROP TABLE users;'
        }
        self.post(self.refresh_url, data=malicious_payload, status_code=200)

        token_entry = RefreshTokenWhitelistModel.objects.latest('created')
        self.assertNotIn('<script>', token_entry.browser)
        self.assertEqual(token_entry.ip, '127.0.0.1')

    def test_expired_token_refresh(self):
        expired_token = self.TOKEN
        expired_token.set_exp(lifetime=-timedelta(days=1000))

        payload = {'refresh': str(expired_token)}
        resp = self.post(self.refresh_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], 'token_not_valid')

    def test_replay_attack_protection(self):
        payload = {'refresh': str(self.TOKEN)}

        self.post(self.refresh_url, data=payload, status_code=200)

        resp = self.post(self.refresh_url, data=payload, status_code=401)
        self.assertEqual(resp['code'], 'token_not_valid')

    def test_targeted_session_deletion(self):
        payload = {'refresh': str(self.TOKEN)}

        time.sleep(1)  # wait for 1 second to make sure the new expiration is different
        self.post(self.refresh_url, data=payload, status_code=200)

        # new session
        resp = self.post(self.login_url, data=self.LOGIN_PAYLOAD, status_code=200)
        new_session_token = RefreshToken(resp['refresh'])

        # suspicious activity (token refresh reused) - only this session is revoked
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())
        self.post(self.refresh_url, data=payload, status_code=401)
        self.assertFalse(RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(user=new_session_token['user_id']).exists())

        new_session_payload = {'refresh': str(new_session_token)}
        self.post(self.refresh_url, data=new_session_payload, status_code=200)

    def test_token_claims_integrity(self):
        payload = {'refresh': str(self.TOKEN)}
        resp = self.post(self.refresh_url, data=payload, status_code=200)
        new_token = RefreshToken(resp['refresh'])

        self.assertEqual(new_token.payload['user_id'], self.USER.id)
        self.assertTrue(new_token.payload['exp'] > datetime.now().timestamp())
        self.assertTrue(new_token.payload['iat'] < datetime.now().timestamp())
