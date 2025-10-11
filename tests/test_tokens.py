import time
from unittest.mock import Mock
from datetime import datetime, timedelta

from allauth.account.models import EmailAddress
from django.test import override_settings

from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.tokens import RefreshToken
from jwt_allauth.tokens.tokens import RefreshToken as RefreshTokenClass
from .mixins import TestsMixin
from jwt_allauth.constants import REFRESH_TOKEN_COOKIE


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
        self.client.cookies[REFRESH_TOKEN_COOKIE] = 'dummy_refresh'

        resp = self.post(self.refresh_url, data={}, status_code=401)
        self.assertEqual(resp['code'], u'token_not_valid')

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
    def test_refresh(self):
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(
            jti=self.TOKEN.payload['jti']
        ).filter(session=self.TOKEN.payload['session']).exists())

        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)

        time.sleep(1)  # wait for 1 second to make sure the new expiration is different
        refresh_response = self.client.post(
            self.refresh_url,
            data={},
            format='json'
        )
        self.assertEqual(refresh_response.status_code, 200)
        resp = refresh_response.json()
        self.assertTrue('access' in resp.keys())
        self.assertFalse('refresh' in resp.keys())  # Should be in cookie, not payload
        new_token = RefreshToken(refresh_response.cookies[REFRESH_TOKEN_COOKIE].value)

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

        # suspicious activity (token refresh reused) - test with old cookie
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)  # Try to reuse old token
        reuse_response = self.client.post(
            self.refresh_url,
            data={},
            format='json'
        )
        self.assertEqual(reuse_response.status_code, 401)
        resp = reuse_response.json()
        self.assertEqual(resp['code'], u'token_not_valid')
        self.assertTrue(not RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())

    def test_refresh_token_disabled(self):
        token_object = RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti'])[0]
        token_object.enabled = False
        token_object.save()

        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)

        resp = self.post(self.refresh_url, data={}, status_code=401)
        self.assertEqual(resp['code'], u'token_not_valid')

    def test_refresh_not_verified_email(self):
        EmailAddress.objects.filter(user=self.USER).delete()
        token_object = RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti'])[0]
        token_object.enabled = False
        token_object.save()

        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)

        resp = self.post(self.refresh_url, data={}, status_code=401)
        self.assertEqual(resp['code'], u'email_not_verified')

    def test_refresh_not_whitelisted(self):
        RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti']).delete()

        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)

        resp = self.post(self.refresh_url, data={}, status_code=401)
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
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        malicious_payload = {
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

        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(expired_token)
        resp = self.post(self.refresh_url, data={}, status_code=401)
        self.assertEqual(resp['code'], 'token_not_valid')

    def test_replay_attack_protection(self):
        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)

        self.post(self.refresh_url, data={}, status_code=200)

        # Try to reuse the same token (replay attack)
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        resp = self.post(self.refresh_url, data={}, status_code=401)
        self.assertEqual(resp['code'], 'token_not_valid')

    def test_targeted_session_deletion(self):
        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)

        time.sleep(1)  # wait for 1 second to make sure the new expiration is different
        self.post(self.refresh_url, data={}, status_code=200)

        # new session
        login_response = self.client.post(
            self.login_url,
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertEqual(login_response.status_code, 200)
        new_session_token = RefreshToken(login_response.cookies[REFRESH_TOKEN_COOKIE].value)

        # suspicious activity (token refresh reused) - only this session is revoked
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)  # Try to reuse old token
        self.post(self.refresh_url, data={}, status_code=401)
        self.assertFalse(RefreshTokenWhitelistModel.objects.filter(session=self.TOKEN.payload['session']).exists())
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(user=new_session_token['user_id']).exists())

        # Test new session still works
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(new_session_token)
        self.post(self.refresh_url, data={}, status_code=200)

    def test_token_claims_integrity(self):
        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        refresh_response = self.client.post(
            self.refresh_url,
            data={},
            format='json'
        )
        self.assertEqual(refresh_response.status_code, 200)
        new_token = RefreshToken(refresh_response.cookies[REFRESH_TOKEN_COOKIE].value)

        self.assertEqual(str(new_token.payload['user_id']), str(self.USER.id))
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

        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        refresh_response = self.client.post(
            self.refresh_url,
            data={},
            format='json',
            **headers
        )
        new_token = RefreshToken(refresh_response.cookies[REFRESH_TOKEN_COOKIE].value)

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

    def test_refresh_token_from_cookie_default(self):
        """Test that refresh token is sent and received via cookie by default"""
        # First, login to get tokens via cookie
        login_response = self.client.post(
            self.login_url,
            data=self.LOGIN_PAYLOAD,
            format='json'
        )

        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        self.assertIn('access', login_data)
        self.assertNotIn('refresh', login_data)  # Should not be in payload
        self.assertIn(REFRESH_TOKEN_COOKIE, login_response.cookies)

        # Now test refresh using the cookie
        time.sleep(.1)  # wait for 0.1 second to make sure the new expiration is different

        # Don't send refresh in payload, it should come from cookie
        refresh_response = self.client.post(
            self.refresh_url,
            data={},
            format='json'
        )

        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        self.assertIn('access', refresh_data)
        self.assertNotIn('refresh', refresh_data)  # Should not be in payload
        self.assertIn(REFRESH_TOKEN_COOKIE, refresh_response.cookies)

    @override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False)
    def test_refresh_token_in_payload_when_configured(self):
        """Test that refresh token is sent and received via payload when configured"""
        # First, login to get tokens via payload
        login_response = self.client.post(
            self.login_url,
            data=self.LOGIN_PAYLOAD,
            format='json'
        )

        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        self.assertIn('access', login_data)
        self.assertIn('refresh', login_data)  # Should be in payload
        self.assertNotIn(REFRESH_TOKEN_COOKIE, login_response.cookies)

        # Now test refresh using the payload
        time.sleep(.1)  # wait for 0.1 second to make sure the new expiration is different

        payload = {'refresh': login_data['refresh']}
        refresh_response = self.client.post(
            self.refresh_url,
            data=payload,
            format='json'
        )

        self.assertEqual(refresh_response.status_code, 200)
        refresh_data = refresh_response.json()
        self.assertIn('access', refresh_data)
        self.assertIn('refresh', refresh_data)  # Should be in payload
        self.assertNotIn(REFRESH_TOKEN_COOKIE, refresh_response.cookies)

    def test_refresh_token_cookie_missing_error(self):
        """Test that missing refresh token cookie returns error"""
        # Try to refresh without cookie or payload
        resp = self.post(self.refresh_url, data={}, status_code=400)
        self.assertIn('refresh', resp)  # Should have validation error

    @override_settings(JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False)
    def test_refresh_token_payload_missing_error_when_configured(self):
        """Test that missing refresh token in payload returns error when configured for payload"""
        # Try to refresh without payload
        resp = self.post(self.refresh_url, data={}, status_code=400)
        self.assertIn('refresh', resp)  # Should have validation error

    @override_settings(JWT_ALLAUTH_COLLECT_USER_AGENT=True)
    def test_user_agent_automatic_collection(self):
        """Verify user agent info is collected automatically and can't be sent in request when collection is enabled"""
        # Set custom headers to simulate a specific user agent
        headers = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',  # noqa: E501
            'HTTP_X_FORWARDED_FOR': '192.168.1.200'
        }

        # Set cookie for refresh and attempt to send user agent data in request body (should be ignored)
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        malicious_payload = {
            'ip': 'malicious-ip',
            'browser': 'MaliciousBrowser',
            'os': 'MaliciousOS',
            'device': 'MaliciousDevice'
        }

        refresh_response = self.client.post(
            self.refresh_url,
            data=malicious_payload,
            format='json',
            **headers
        )
        self.assertEqual(refresh_response.status_code, 200)
        new_token = RefreshToken(refresh_response.cookies[REFRESH_TOKEN_COOKIE].value)

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

        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        refresh_response = self.client.post(
            self.refresh_url,
            data={},
            format='json',
            **headers
        )
        new_token = RefreshToken(refresh_response.cookies[REFRESH_TOKEN_COOKIE].value)

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

        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        refresh_response = self.client.post(
            self.refresh_url,
            data={},
            format='json',
            **headers
        )
        new_token = RefreshToken(refresh_response.cookies[REFRESH_TOKEN_COOKIE].value)

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

        # Set cookie for refresh
        self.client.cookies[REFRESH_TOKEN_COOKIE] = str(self.TOKEN)
        refresh_response = self.client.post(
            self.refresh_url,
            data={},
            format='json',
            **headers
        )
        self.assertEqual(refresh_response.status_code, 200)
        new_token = RefreshToken(refresh_response.cookies[REFRESH_TOKEN_COOKIE].value)

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

    @override_settings(JWT_ALLAUTH_USER_ATTRIBUTES={'email': 'email', 'username': 'username'})
    def test_set_user_attributes_with_valid_user_attributes(self):
        """Verify that set_user_attributes correctly adds configured user attributes to token payload"""
        token = RefreshTokenClass()

        # Create a mock user with the attributes we want to test
        user = Mock()
        user.email = 'test@example.com'
        user.username = 'testuser'

        token.set_user_attributes(user)

        # Verify the attributes are added to the payload
        self.assertEqual(token.payload['email'], 'test@example.com')
        self.assertEqual(token.payload['username'], 'testuser')

    @override_settings(JWT_ALLAUTH_USER_ATTRIBUTES={'role': 'profile.role', 'name': 'profile.department.name'})
    def test_set_user_attributes_with_nested_attribute_paths(self):
        """Verify that set_user_attributes correctly handles nested attribute paths"""
        token = RefreshTokenClass()

        # Create nested mock objects
        department = Mock()
        department.name = 'Engineering'

        profile = Mock()
        profile.role = 'admin'
        profile.department = department

        user = Mock()
        user.profile = profile

        # Including a final attribute name 'role' is incompatible and should raise
        with self.assertRaises(ValueError):
            token.set_user_attributes(user)

    @override_settings(JWT_ALLAUTH_USER_ATTRIBUTES={'email': 'email', 'nonexistent_attr': 'nonexistent_attr', 'missing': 'profile.missing'})
    def test_set_user_attributes_with_missing_attributes(self):
        """Verify that set_user_attributes handles missing or None attributes gracefully"""
        token = RefreshTokenClass()

        user = Mock()
        user.email = 'test@example.com'
        # nonexistent_attr and profile.missing are not set, so they should be None

        token.set_user_attributes(user)

        # Only the existing attribute should be in the payload
        self.assertEqual(token.payload['email'], 'test@example.com')
        self.assertNotIn('nonexistent_attr', token.payload)
        self.assertNotIn('missing', token.payload)

    @override_settings(JWT_ALLAUTH_USER_ATTRIBUTES={'role': 'role', 'email': 'email'})
    def test_set_user_attributes_prevents_role_attribute_collision(self):
        """Verify that set_user_attributes does not overwrite existing 'role' attribute"""
        token = RefreshTokenClass()

        # First set the role via set_user_role (as done in for_user)
        user = Mock()
        user.role = 'admin'
        user.email = 'test@example.com'

        token.set_user_role(user)
        # Configuration including 'role' must be rejected
        with self.assertRaises(ValueError):
            token.set_user_attributes(user)

    @override_settings(JWT_ALLAUTH_USER_ATTRIBUTES={'email': 'email', 'username': 'username', 'title': 'profile.title'})
    def test_for_user_includes_user_attributes_in_token(self):
        """Verify that RefreshToken.for_user method calls set_user_attributes and includes user attributes"""
        # Use a real persisted user to satisfy whitelist serializer
        user = self.USER
        user.email = 'test@example.com'
        user.username = 'testuser'
        user.save()

        # Attach a profile-like object with title
        profile = Mock()
        profile.title = 'Developer'
        user.profile = profile

        # Generate token using for_user
        token = RefreshTokenClass.for_user(user)

        # Verify user attributes are included in the payload
        self.assertEqual(token.payload['email'], 'test@example.com')
        self.assertEqual(token.payload['username'], 'testuser')
        self.assertEqual(token.payload['title'], 'Developer')
