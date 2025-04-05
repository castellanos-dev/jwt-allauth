import time

from django.contrib.auth import get_user_model
from django.test import override_settings

from jwt_allauth.token.models import RefreshTokenWhitelistModel
from jwt_allauth.token.tokens import RefreshToken
from .mixins import TestsMixin


@override_settings(ROOT_URLCONF="tests.urls")
class LogoutTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    def setUp(self):
        self.init()

    def test_logout_no_authorized(self):
        resp = self.post(self.logout_url, status_code=401)
        self.assertEqual(resp['detail'], u'Authentication credentials were not provided.')

    def test_logout_all(self):
        _ = RefreshToken().for_user(self.USER)

        self.assertTrue(len(RefreshTokenWhitelistModel.objects.filter(user=self.USER).values_list()) == 2)

        self.token = self.ACCESS

        resp = self.post(self.logout_all_url, status_code=200)
        self.assertEqual(resp['detail'], u'Successfully logged out from all devices.')

        self.assertTrue(not RefreshTokenWhitelistModel.objects.filter(user=self.USER).exists())

    def test_logout_with_refresh_token(self):
        new_token = RefreshToken().for_user(self.USER)

        self.token = self.ACCESS

        self.assertTrue(len(RefreshTokenWhitelistModel.objects.filter(user=self.USER).values_list()) == 2)

        resp = self.post(self.logout_url, data={'refresh': str(self.TOKEN)}, status_code=200)
        self.assertEqual(resp['detail'], u'Successfully logged out.')

        self.assertTrue(not RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti']).exists())
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(jti=new_token.payload['jti']).exists())
        self.assertTrue(len(RefreshTokenWhitelistModel.objects.filter(user=self.USER).values_list()) == 1)

    def test_logout_with_refresh_token_not_valid(self):
        new_token = RefreshToken().for_user(self.USER)

        self.token = self.ACCESS

        self.assertTrue(len(RefreshTokenWhitelistModel.objects.filter(user=self.USER).values_list()) == 2)

        self.post(self.logout_url, data={'refresh': 'dummy'}, status_code=400)

        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti']).exists())
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(jti=new_token.payload['jti']).exists())
        self.assertTrue(len(RefreshTokenWhitelistModel.objects.filter(user=self.USER).values_list()) == 2)

    def test_logout_with_refresh_token_not_whitelisted(self):
        new_token = RefreshToken().for_user(self.USER)

        new_token2 = RefreshToken().for_user(self.USER)
        RefreshTokenWhitelistModel.objects.filter(
            user=self.USER,
            jti=new_token2.payload['jti'],
            session=new_token2.payload['session'],
        ).delete()

        self.token = self.ACCESS

        self.assertTrue(len(RefreshTokenWhitelistModel.objects.filter(user=self.USER).values_list()) == 2)

        self.post(self.logout_url, data={'refresh': str(new_token2)}, status_code=400)

        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(jti=self.TOKEN.payload['jti']).exists())
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(jti=new_token.payload['jti']).exists())
        self.assertTrue(len(RefreshTokenWhitelistModel.objects.filter(user=self.USER).values_list()) == 2)

    def test_logout_methods_not_allowed(self):
        self.token = self.ACCESS

        resp = self.get(self.logout_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "GET" not allowed.')
        resp = self.put(self.logout_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.patch(self.logout_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PATCH" not allowed.')
        resp = self.delete(self.logout_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')

    def test_logout_missing_refresh_token(self):
        self.token = self.ACCESS
        resp = self.post(self.logout_url, data={}, status_code=400)
        self.assertEqual(resp['refresh'][0], 'This field is required.')

    def test_logout_another_users_token(self):
        user2 = get_user_model().objects.create_user(username='user2', password='password')
        refresh_user2 = RefreshToken().for_user(user2)

        self.token = self.ACCESS  # self.USER token
        resp = self.post(self.logout_url, data={'refresh': str(refresh_user2)}, status_code=400)

        self.assertEqual(resp['detail'], 'Invalid token.')
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(jti=refresh_user2.payload['jti']).exists())

    def test_logout_expired_refresh_token(self):
        refresh = RefreshToken().for_user(self.USER)
        refresh['exp'] = int(time.time())

        self.token = str(refresh.access_token)
        refresh_token = str(refresh)
        time.sleep(0.1)
        resp = self.post(self.logout_url, data={'refresh': refresh_token}, status_code=400)
        self.assertIn('Invalid token.', resp['detail'])

    def test_logout_idempotency(self):
        self.token = self.ACCESS
        self.post(self.logout_url, data={'refresh': str(self.TOKEN)}, status_code=200)
        resp = self.post(self.logout_url, data={'refresh': str(self.TOKEN)}, status_code=400)
        self.assertIn('Invalid token.', resp['detail'])

    def test_tampered_token_logout(self):
        self.token = self.ACCESS
        tampered_token = str(self.TOKEN) + 'tampered'
        resp = self.post(self.logout_url, data={'refresh': tampered_token}, status_code=400)
        self.assertEqual(resp['detail'], 'Invalid token.')
