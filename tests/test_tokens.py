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

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
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

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
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

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
    def test_user_agent_storage(self):
        """Verify user agent information is stored correctly when collection is enabled"""
        # Set custom headers to simulate different user agent
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',  # noqa: E501
            'HTTP_X_FORWARDED_FOR': '192.168.1.100'
        }

        payload = {'refresh': str(self.TOKEN)}
        resp = self.post(self.refresh_url, data=payload, status_code=200, **headers)
        new_token = RefreshToken(resp['refresh'])

        # Retrieve the token entry from database
        token_entry = RefreshTokenWhitelistModel.objects.get(jti=new_token.payload['jti'])

        # Verify IP address storage
        self.assertEqual(token_entry.ip, '192.168.1.100')

        # Verify device information
        self.assertEqual(token_entry.browser, 'Chrome')
        self.assertEqual(token_entry.browser_version, '91.0.4472')
        self.assertEqual(token_entry.os, 'Mac OS X')
        self.assertEqual(token_entry.os_version, '10.15.7')
        self.assertEqual(token_entry.device, 'Mac')
        self.assertEqual(token_entry.device_brand, 'Apple')
        self.assertEqual(token_entry.device_model, 'Mac')
        self.assertTrue(token_entry.is_pc)
        self.assertFalse(token_entry.is_mobile)
        self.assertFalse(token_entry.is_tablet)
        self.assertFalse(token_entry.is_bot)

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
    def test_user_agent_automatic_collection(self):
        """Verify user agent info is collected automatically and can't be sent in request when collection is enabled"""
        # Set custom headers to simulate a specific user agent
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',  # noqa: E501
            'HTTP_X_FORWARDED_FOR': '192.168.1.200'
        }

        # Attempt to send user agent data in request body (should be ignored)
        payload = {
            'refresh': str(self.TOKEN),
            'ip': 'malicious-ip',
            'browser': 'MaliciousBrowser',
            'os': 'MaliciousOS',
            'device': 'MaliciousDevice'
        }

        resp = self.post(self.refresh_url, data=payload, status_code=200, **headers)
        new_token = RefreshToken(resp['refresh'])

        # Retrieve the token entry from database
        token_entry = RefreshTokenWhitelistModel.objects.get(jti=new_token.payload['jti'])

        # Verify that the actual headers were used, not the payload values
        self.assertEqual(token_entry.ip, '192.168.1.200')
        self.assertEqual(token_entry.browser, 'Chrome')
        self.assertEqual(token_entry.browser_version, '91.0.4472')
        self.assertEqual(token_entry.os, 'Windows')
        self.assertEqual(token_entry.os_version, '10')
        self.assertEqual(token_entry.device, 'Other')
        self.assertTrue(token_entry.is_pc)

        # Verify malicious values from payload were ignored
        self.assertNotEqual(token_entry.ip, 'malicious-ip')
        self.assertNotEqual(token_entry.browser, 'MaliciousBrowser')
        self.assertNotEqual(token_entry.os, 'MaliciousOS')
        self.assertNotEqual(token_entry.device, 'MaliciousDevice')

    def test_user_agent_collection_disabled_by_default(self):
        """Verify user agent information is NOT collected by default (when JWT_ALLAUTH_COLLECT_USER_AGENT=False)"""
        # Set custom headers to simulate different user agent
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',  # noqa: E501
            'HTTP_X_FORWARDED_FOR': '192.168.1.100'
        }

        payload = {'refresh': str(self.TOKEN)}
        resp = self.post(self.refresh_url, data=payload, status_code=200, **headers)
        new_token = RefreshToken(resp['refresh'])

        # Retrieve the token entry from database
        token_entry = RefreshTokenWhitelistModel.objects.get(jti=new_token.payload['jti'])

        # Verify user agent information is NOT stored (should be None or empty)
        self.assertIsNone(token_entry.ip)
        self.assertIsNone(token_entry.browser)
        self.assertIsNone(token_entry.browser_version)
        self.assertIsNone(token_entry.os)
        self.assertIsNone(token_entry.os_version)
        self.assertIsNone(token_entry.device)
        self.assertIsNone(token_entry.device_brand)
        self.assertIsNone(token_entry.device_model)
        self.assertIsNone(token_entry.is_pc)
        self.assertIsNone(token_entry.is_mobile)
        self.assertIsNone(token_entry.is_tablet)
        self.assertIsNone(token_entry.is_bot)

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=False)
    def test_user_agent_collection_explicitly_disabled(self):
        """Verify user agent information is NOT collected when JWT_ALLAUTH_COLLECT_USER_AGENT=False"""
        # Set custom headers to simulate different user agent
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',  # noqa: E501
            'HTTP_X_FORWARDED_FOR': '10.0.0.50'
        }

        payload = {'refresh': str(self.TOKEN)}
        resp = self.post(self.refresh_url, data=payload, status_code=200, **headers)
        new_token = RefreshToken(resp['refresh'])

        # Retrieve the token entry from database
        token_entry = RefreshTokenWhitelistModel.objects.get(jti=new_token.payload['jti'])

        # Verify user agent information is NOT stored
        self.assertIsNone(token_entry.ip)
        self.assertIsNone(token_entry.browser)
        self.assertIsNone(token_entry.browser_version)
        self.assertIsNone(token_entry.os)
        self.assertIsNone(token_entry.os_version)
        self.assertIsNone(token_entry.device)
        self.assertIsNone(token_entry.device_brand)
        self.assertIsNone(token_entry.device_model)
        self.assertIsNone(token_entry.is_pc)
        self.assertIsNone(token_entry.is_mobile)
        self.assertIsNone(token_entry.is_tablet)
        self.assertIsNone(token_entry.is_bot)

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
    def test_user_agent_collection_enabled(self):
        """Verify user agent information IS collected when JWT_ALLAUTH_COLLECT_USER_AGENT=True"""
        # Set custom headers to simulate mobile user agent
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',  # noqa: E501
            'HTTP_X_FORWARDED_FOR': '10.0.0.50'
        }

        payload = {'refresh': str(self.TOKEN)}
        resp = self.post(self.refresh_url, data=payload, status_code=200, **headers)
        new_token = RefreshToken(resp['refresh'])

        # Retrieve the token entry from database
        token_entry = RefreshTokenWhitelistModel.objects.get(jti=new_token.payload['jti'])

        # Verify user agent information IS stored
        self.assertEqual(token_entry.ip, '10.0.0.50')
        self.assertEqual(token_entry.browser, 'Mobile Safari')
        self.assertEqual(token_entry.browser_version, '14.1.1')
        self.assertEqual(token_entry.os, 'iOS')
        self.assertEqual(token_entry.os_version, '14.6')
        self.assertEqual(token_entry.device, 'iPhone')
        self.assertEqual(token_entry.device_brand, 'Apple')
        self.assertEqual(token_entry.device_model, 'iPhone')
        self.assertFalse(token_entry.is_pc)
        self.assertTrue(token_entry.is_mobile)
        self.assertFalse(token_entry.is_tablet)
        self.assertFalse(token_entry.is_bot)
