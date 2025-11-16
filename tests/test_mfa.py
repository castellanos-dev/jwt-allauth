"""
Tests for MFA (Multi-Factor Authentication) TOTP functionality

These tests comprehensively verify the MFA TOTP implementation, including:
- Setup and initialization of TOTP
- Activation with code verification
- Listing and managing authenticators
- Deactivation with password verification
- Verification flows during login
- Recovery code handling
- Complete end-to-end flows
"""
import uuid
from unittest.mock import patch, MagicMock

from allauth.mfa.models import Authenticator
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from jwt_allauth.constants import (
    MFA_TOKEN_MAX_AGE_SECONDS,
    MFA_TOTP_DISABLED,
    MFA_TOTP_OPTIONAL,
    MFA_TOTP_REQUIRED,
)
from .mixins import TestsMixin


class MFASetupTests(TestsMixin):
    """
    Tests for MFA Setup endpoint - initializes TOTP setup
    """

    def setUp(self):
        self.init()
        self._login()
        self.setup_url = reverse('jwt_allauth_mfa_setup')

    def tearDown(self):
        cache.clear()

    def test_setup_not_authenticated(self):
        """Test that setup endpoint requires authentication"""
        # Remove token to simulate unauthenticated request
        if hasattr(self, 'token'):
            del self.token

        resp = self.post(self.setup_url, data={}, status_code=401)
        self.assertIn('detail', resp)

    def test_setup_requires_post_method(self):
        """Test that setup only accepts POST requests"""
        resp = self.get(self.setup_url, status_code=405)
        self.assertEqual(resp['detail'], 'Method "GET" not allowed.')

        resp = self.put(self.setup_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], 'Method "PUT" not allowed.')

        resp = self.patch(self.setup_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], 'Method "PATCH" not allowed.')

        resp = self.delete(self.setup_url, status_code=405)
        self.assertEqual(resp['detail'], 'Method "DELETE" not allowed.')

    def test_setup_success(self):
        """Test successful TOTP setup initialization"""
        resp = self.post(self.setup_url, data={}, status_code=200)

        # Should return secret, provisioning URI, and QR code
        self.assertIn('secret', resp)
        self.assertIn('provisioning_uri', resp)
        self.assertIn('qr_code', resp)

        # Verify secret format (base32 encoded)
        self.assertTrue(len(resp['secret']) > 0)
        self.assertTrue(len(resp['provisioning_uri']) > 0)
        self.assertTrue(len(resp['qr_code']) > 0)

    def test_setup_caches_secret(self):
        """Test that setup stores secret in cache"""
        self.post(self.setup_url, data={}, status_code=200)

        # Verify secret is cached with correct key
        cache_key = f"mfa_setup:{self.USER.id}"
        cached_secret = cache.get(cache_key)
        self.assertIsNotNone(cached_secret)

    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE=MFA_TOTP_DISABLED)
    def test_setup_disabled_mode(self):
        """Test that setup returns 403 when MFA is disabled"""
        resp = self.post(self.setup_url, data={}, status_code=403)
        self.assertEqual(resp['detail'], 'MFA TOTP is disabled.')

    def test_setup_totp_already_activated(self):
        """Test that setup prevents re-activation of TOTP"""
        # Activate TOTP first using the proper django-allauth API
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP,
            data={'secret': 'test_secret'}
        )

        # Try to setup again
        resp = self.post(self.setup_url, data={}, status_code=400)
        self.assertEqual(resp['detail'], 'TOTP already activated.')


class MFAActivateTests(TestsMixin):
    """
    Tests for MFA Activation endpoint - confirms TOTP code and activates MFA
    """

    def setUp(self):
        self.init()
        self._login()
        self.setup_url = reverse('jwt_allauth_mfa_setup')
        self.activate_url = reverse('jwt_allauth_mfa_activate')

    def tearDown(self):
        cache.clear()

    def test_activate_not_authenticated(self):
        """Test that activate endpoint requires authentication"""
        if hasattr(self, 'token'):
            del self.token

        resp = self.post(self.activate_url, data={'code': '000000'}, status_code=401)
        self.assertIn('detail', resp)

    def test_activate_missing_code(self):
        """Test activation fails with missing code"""
        resp = self.post(self.activate_url, data={}, status_code=400)
        self.assertIn('code', resp)

    def test_activate_invalid_code_format(self):
        """Test activation fails with invalid code format"""
        # Code must be 6 digits
        resp = self.post(
            self.activate_url,
            data={'code': '12345'},  # Too short
            status_code=400
        )
        self.assertIn('code', resp)

        resp = self.post(
            self.activate_url,
            data={'code': '1234567'},  # Too long
            status_code=400
        )
        self.assertIn('code', resp)

    def test_activate_no_setup_initiated(self):
        """Test activation fails when setup was not initiated"""
        resp = self.post(
            self.activate_url,
            data={'code': '000000'},
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Setup not initiated.')

    @patch('jwt_allauth.mfa.views.TOTP')
    def test_activate_invalid_totp_code(self, mock_totp_class):
        """Test activation fails with invalid TOTP code"""
        # Setup
        self.post(self.setup_url, data={}, status_code=200)

        # Mock TOTP validation to return False
        mock_totp_instance = MagicMock()
        mock_totp_instance.validate_code.return_value = False
        mock_totp_instance.instance = MagicMock()
        mock_totp_class.activate.return_value = mock_totp_instance

        # Try to activate with wrong code
        resp = self.post(
            self.activate_url,
            data={'code': '000000'},
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Invalid code.')

    @patch('jwt_allauth.mfa.views.TOTP')
    @patch('jwt_allauth.mfa.views.RecoveryCodes')
    def test_activate_valid_totp_code(self, mock_recovery_class, mock_totp_class):
        """Test successful TOTP activation with valid code"""
        # Setup
        self.post(self.setup_url, data={}, status_code=200)

        # Mock TOTP validation to return True
        mock_totp_instance = MagicMock()
        mock_totp_instance.validate_code.return_value = True
        mock_totp_instance.instance = MagicMock()
        mock_totp_class.activate.return_value = mock_totp_instance

        # Mock recovery codes
        mock_recovery_instance = MagicMock()
        mock_recovery_instance.get_unused_codes.return_value = ['CODE1', 'CODE2', 'CODE3']
        mock_recovery_class.activate.return_value = mock_recovery_instance

        # Activate with valid code
        resp = self.post(
            self.activate_url,
            data={'code': '123456'},
            status_code=200
        )

        self.assertTrue(resp['success'])
        self.assertIn('recovery_codes', resp)
        self.assertEqual(len(resp['recovery_codes']), 3)

    @patch('jwt_allauth.mfa.views.TOTP')
    @patch('jwt_allauth.mfa.views.RecoveryCodes')
    def test_activate_cache_cleared_after_success(self, mock_recovery_class, mock_totp_class):
        """Test that setup cache is cleared after successful activation"""
        # Setup
        resp = self.post(self.setup_url, data={}, status_code=200)
        secret = resp['secret']

        # Verify cache exists
        cache_key = f"mfa_setup:{self.USER.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # Mock TOTP and recovery
        mock_totp_instance = MagicMock()
        mock_totp_instance.validate_code.return_value = True
        mock_totp_instance.instance = MagicMock()
        mock_totp_class.activate.return_value = mock_totp_instance

        mock_recovery_instance = MagicMock()
        mock_recovery_instance.get_unused_codes.return_value = ['CODE1']
        mock_recovery_class.activate.return_value = mock_recovery_instance

        # Activate
        self.post(
            self.activate_url,
            data={'code': '123456'},
            status_code=200
        )

        # Verify cache is cleared
        self.assertIsNone(cache.get(cache_key))

    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE=MFA_TOTP_DISABLED)
    def test_activate_disabled_mode(self):
        """Test that activate returns 403 when MFA is disabled"""
        resp = self.post(self.activate_url, data={}, status_code=403)
        self.assertEqual(resp['detail'], 'MFA TOTP is disabled.')


class MFAListAuthenticatorsTests(TestsMixin):
    """
    Tests for listing authenticators
    """

    def setUp(self):
        self.init()
        self._login()
        self.authenticators_url = reverse('jwt_allauth_mfa_authenticators')

    def test_list_not_authenticated(self):
        """Test that list requires authentication"""
        if hasattr(self, 'token'):
            del self.token

        resp = self.get(self.authenticators_url, status_code=401)
        self.assertIn('detail', resp)

    def test_list_no_authenticators(self):
        """Test listing when user has no authenticators"""
        resp = self.get(self.authenticators_url, status_code=200)
        self.assertEqual(resp, [])

    def test_list_with_authenticators(self):
        """Test listing authenticators for user with MFA enabled"""
        # Create authenticator using the proper django-allauth approach
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        resp = self.get(self.authenticators_url, status_code=200)
        self.assertEqual(len(resp), 1)
        self.assertIn('id', resp[0])
        self.assertIn('type', resp[0])
        self.assertEqual(resp[0]['type'], 'totp')

    def test_list_multiple_authenticators(self):
        """Test listing multiple authenticators"""
        # Create multiple authenticators
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP,
            data={'secret': 'test_secret'}
        )
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.RECOVERY_CODES,
            data={'codes': ['code1', 'code2']}
        )

        resp = self.get(self.authenticators_url, status_code=200)
        self.assertEqual(len(resp), 2)

    def test_list_only_own_authenticators(self):
        """Test that user only sees their own authenticators"""
        from django.contrib.auth import get_user_model

        # Create another user's authenticator
        other_user = get_user_model().objects.create_user(
            username='other',
            email='other@test.com',
            password='password123'
        )
        Authenticator.objects.create(
            user=other_user,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'other_secret'}
        )

        # Create current user's authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        resp = self.get(self.authenticators_url, status_code=200)
        self.assertEqual(len(resp), 1)

    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE=MFA_TOTP_DISABLED)
    def test_list_disabled_mode(self):
        """Test that list returns 403 when MFA is disabled"""
        resp = self.get(self.authenticators_url, status_code=403)
        self.assertEqual(resp['detail'], 'MFA TOTP is disabled.')


class MFADeactivateTests(TestsMixin):
    """
    Tests for MFA Deactivation endpoint
    """

    def setUp(self):
        self.init()
        self._login()
        self.deactivate_url = reverse('jwt_allauth_mfa_deactivate')

    def tearDown(self):
        cache.clear()

    def test_deactivate_not_authenticated(self):
        """Test that deactivate requires authentication"""
        if hasattr(self, 'token'):
            del self.token

        resp = self.post(
            self.deactivate_url,
            data={'password': self.PASS},
            status_code=401
        )
        self.assertIn('detail', resp)

    def test_deactivate_missing_password(self):
        """Test deactivation fails with missing password"""
        resp = self.post(self.deactivate_url, data={}, status_code=400)
        self.assertIn('password', resp)

    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE=MFA_TOTP_REQUIRED)
    def test_deactivate_when_required(self):
        """Test that deactivation fails when MFA is required"""
        # Create authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        resp = self.post(
            self.deactivate_url,
            data={'password': self.PASS},
            status_code=403
        )
        self.assertEqual(resp['detail'], 'MFA TOTP is required and cannot be disabled.')

    def test_deactivate_invalid_password(self):
        """Test deactivation fails with wrong password"""
        # Create authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        resp = self.post(
            self.deactivate_url,
            data={'password': 'WrongPassword'},
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Invalid password.')

    def test_deactivate_no_totp_activated(self):
        """Test deactivation fails when TOTP is not activated"""
        resp = self.post(
            self.deactivate_url,
            data={'password': self.PASS},
            status_code=400
        )
        self.assertEqual(resp['detail'], 'TOTP not activated.')

    def test_deactivate_success(self):
        """Test successful TOTP deactivation"""
        # Create authenticator
        auth = Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        self.assertTrue(Authenticator.objects.filter(id=auth.id).exists())

        # Deactivate
        resp = self.post(
            self.deactivate_url,
            data={'password': self.PASS},
            status_code=200
        )

        self.assertTrue(resp['success'])
        self.assertFalse(Authenticator.objects.filter(id=auth.id).exists())

    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE=MFA_TOTP_DISABLED)
    def test_deactivate_disabled_mode(self):
        """Test that deactivate returns 403 when MFA is disabled"""
        resp = self.post(self.deactivate_url, data={'password': self.PASS}, status_code=403)
        self.assertEqual(resp['detail'], 'MFA TOTP is disabled.')


class MFAVerifyTests(TestsMixin):
    """
    Tests for MFA Verification endpoint - verifies TOTP code during login
    """

    def setUp(self):
        self.init()
        self.verify_url = reverse('jwt_allauth_mfa_verify')

    def tearDown(self):
        cache.clear()

    def test_verify_missing_challenge_id(self):
        """Test verification fails without challenge_id"""
        resp = self.post(
            self.verify_url,
            data={'code': '123456'},
            status_code=400
        )
        self.assertIn('challenge_id', resp)

    def test_verify_missing_code(self):
        """Test verification fails without code"""
        resp = self.post(
            self.verify_url,
            data={'challenge_id': 'test_challenge'},
            status_code=400
        )
        self.assertIn('code', resp)

    def test_verify_invalid_code_format(self):
        """Test verification fails with invalid code format"""
        resp = self.post(
            self.verify_url,
            data={'challenge_id': 'test', 'code': '12345'},
            status_code=400
        )
        self.assertIn('code', resp)

    def test_verify_expired_challenge(self):
        """Test verification fails with expired challenge"""
        # Create a challenge that has already expired
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=0  # Expires immediately
        )

        # Challenge should already be expired
        resp = self.post(
            self.verify_url,
            data={'challenge_id': challenge_id, 'code': '123456'},
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Challenge expired or invalid.')

    def test_verify_invalid_user(self):
        """Test verification fails with non-existent user"""
        # Create challenge with non-existent user
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': 99999},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        resp = self.post(
            self.verify_url,
            data={'challenge_id': challenge_id, 'code': '123456'},
            status_code=404
        )
        self.assertEqual(resp['detail'], 'User not found.')

    def test_verify_user_no_totp(self):
        """Test verification fails when user has no TOTP"""
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        resp = self.post(
            self.verify_url,
            data={'challenge_id': challenge_id, 'code': '123456'},
            status_code=400
        )
        self.assertEqual(resp['detail'], 'TOTP not activated.')

    @patch('jwt_allauth.mfa.views.TOTP')
    def test_verify_invalid_totp_code(self, mock_totp_class):
        """Test verification fails with invalid TOTP code"""
        # Create authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        # Create challenge
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        # Mock invalid TOTP code
        mock_totp_instance = MagicMock()
        mock_totp_instance.validate_code.return_value = False
        mock_totp_class.return_value = mock_totp_instance

        resp = self.post(
            self.verify_url,
            data={'challenge_id': challenge_id, 'code': '000000'},
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Invalid code.')

    @patch('jwt_allauth.mfa.views.TOTP')
    def test_verify_valid_totp_code(self, mock_totp_class):
        """Test successful TOTP verification"""
        # Create authenticator
        auth = Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        # Create challenge
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        # Mock valid TOTP code
        mock_totp_instance = MagicMock()
        mock_totp_instance.validate_code.return_value = True
        mock_totp_class.return_value = mock_totp_instance

        resp = self.post(
            self.verify_url,
            data={'challenge_id': challenge_id, 'code': '123456'},
            status_code=200
        )

        # Should return access token
        self.assertIn('access', resp)

    @patch('jwt_allauth.mfa.views.TOTP')
    def test_verify_challenge_cleared_after_success(self, mock_totp_class):
        """Test that challenge is cleared after successful verification"""
        # Create authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.TOTP.value,
            data={'secret': 'test_secret'}
        )

        # Create challenge
        challenge_id = str(uuid.uuid4())
        challenge_key = f"mfa_challenge:{challenge_id}"
        cache.set(
            challenge_key,
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        # Mock valid TOTP code
        mock_totp_instance = MagicMock()
        mock_totp_instance.validate_code.return_value = True
        mock_totp_class.return_value = mock_totp_instance

        # Verify
        self.post(
            self.verify_url,
            data={'challenge_id': challenge_id, 'code': '123456'},
            status_code=200
        )

        # Verify challenge is cleared
        self.assertIsNone(cache.get(challenge_key))

    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE=MFA_TOTP_DISABLED)
    def test_verify_disabled_mode(self):
        """Test that verify returns 403 when MFA is disabled"""
        resp = self.post(self.verify_url, data={'challenge_id': 'test_challenge', 'code': '123456'}, status_code=403)
        self.assertEqual(resp['detail'], 'MFA TOTP is disabled.')

class MFAVerifyRecoveryTests(TestsMixin):
    """
    Tests for MFA Recovery Code Verification
    """

    def setUp(self):
        self.init()
        self.verify_recovery_url = reverse('jwt_allauth_mfa_verify_recovery')

    def tearDown(self):
        cache.clear()

    def test_verify_recovery_missing_challenge_id(self):
        """Test recovery verification fails without challenge_id"""
        resp = self.post(
            self.verify_recovery_url,
            data={'recovery_code': 'TEST-CODE-001'},
            status_code=400
        )
        self.assertIn('challenge_id', resp)

    def test_verify_recovery_missing_code(self):
        """Test recovery verification fails without recovery_code"""
        resp = self.post(
            self.verify_recovery_url,
            data={'challenge_id': 'test_challenge'},
            status_code=400
        )
        self.assertIn('recovery_code', resp)

    def test_verify_recovery_expired_challenge(self):
        """Test recovery verification fails with expired challenge"""
        # Create a challenge that has already expired
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=0  # Expires immediately
        )

        resp = self.post(
            self.verify_recovery_url,
            data={
                'challenge_id': challenge_id,
                'recovery_code': 'TEST-CODE-001'
            },
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Challenge expired or invalid.')

    def test_verify_recovery_invalid_user(self):
        """Test recovery verification fails with non-existent user"""
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': 99999},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        resp = self.post(
            self.verify_recovery_url,
            data={
                'challenge_id': challenge_id,
                'recovery_code': 'TEST-CODE-001'
            },
            status_code=404
        )
        self.assertEqual(resp['detail'], 'User not found.')

    def test_verify_recovery_no_recovery_codes(self):
        """Test recovery verification fails when user has no recovery codes"""
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        resp = self.post(
            self.verify_recovery_url,
            data={
                'challenge_id': challenge_id,
                'recovery_code': 'TEST-CODE-001'
            },
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Recovery codes not available.')

    @patch('jwt_allauth.mfa.views.RecoveryCodes')
    def test_verify_recovery_invalid_code(self, mock_recovery_class):
        """Test recovery verification fails with invalid code"""
        # Create recovery codes authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.RECOVERY_CODES.value,
            data={'codes': ['CODE1', 'CODE2']}
        )

        # Create challenge
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        # Mock invalid recovery code
        mock_rc_instance = MagicMock()
        mock_rc_instance.validate_code.return_value = False
        mock_recovery_class.return_value = mock_rc_instance

        resp = self.post(
            self.verify_recovery_url,
            data={
                'challenge_id': challenge_id,
                'recovery_code': 'INVALID-CODE'
            },
            status_code=400
        )
        self.assertEqual(resp['detail'], 'Invalid recovery code.')

    @patch('jwt_allauth.mfa.views.RecoveryCodes')
    def test_verify_recovery_valid_code(self, mock_recovery_class):
        """Test successful recovery code verification"""
        # Create recovery codes authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.RECOVERY_CODES,
            data={'codes': ['CODE1', 'CODE2']}
        )

        # Create challenge
        challenge_id = str(uuid.uuid4())
        cache.set(
            f"mfa_challenge:{challenge_id}",
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        # Mock valid recovery code
        mock_rc_instance = MagicMock()
        mock_rc_instance.validate_code.return_value = True
        mock_recovery_class.return_value = mock_rc_instance

        resp = self.post(
            self.verify_recovery_url,
            data={
                'challenge_id': challenge_id,
                'recovery_code': 'CODE1'
            },
            status_code=200
        )

        # Should return access token
        self.assertIn('access', resp)

    @patch('jwt_allauth.mfa.views.RecoveryCodes')
    def test_verify_recovery_challenge_cleared(self, mock_recovery_class):
        """Test that challenge is cleared after successful recovery verification"""
        # Create recovery codes authenticator
        Authenticator.objects.create(
            user=self.USER,
            type=Authenticator.Type.RECOVERY_CODES,
            data={'codes': ['CODE1', 'CODE2']}
        )

        # Create challenge
        challenge_id = str(uuid.uuid4())
        challenge_key = f"mfa_challenge:{challenge_id}"
        cache.set(
            challenge_key,
            {'user_id': self.USER.id},
            timeout=MFA_TOKEN_MAX_AGE_SECONDS
        )

        # Mock valid recovery code
        mock_rc_instance = MagicMock()
        mock_rc_instance.validate_code.return_value = True
        mock_recovery_class.return_value = mock_rc_instance

        # Verify
        self.post(
            self.verify_recovery_url,
            data={
                'challenge_id': challenge_id,
                'recovery_code': 'CODE1'
            },
            status_code=200
        )

        # Verify challenge is cleared
        self.assertIsNone(cache.get(challenge_key))

    @override_settings(JWT_ALLAUTH_MFA_TOTP_MODE=MFA_TOTP_DISABLED)
    def test_verify_recovery_disabled_mode(self):
        """Test that verify recovery returns 403 when MFA is disabled"""
        resp = self.post(self.verify_recovery_url, data={
            'challenge_id': 'test_challenge', 'recovery_code': 'TEST-CODE-001'}, status_code=403)
        self.assertEqual(resp['detail'], 'MFA TOTP is disabled.')


class MFACompleteFlowTests(TestsMixin):
    """
    Integration tests for complete MFA flow
    """

    def setUp(self):
        self.init()
        self._login()
        self.setup_url = reverse('jwt_allauth_mfa_setup')
        self.activate_url = reverse('jwt_allauth_mfa_activate')
        self.verify_url = reverse('jwt_allauth_mfa_verify')
        self.authenticators_url = reverse('jwt_allauth_mfa_authenticators')
        self.deactivate_url = reverse('jwt_allauth_mfa_deactivate')

    def tearDown(self):
        cache.clear()

    @patch('jwt_allauth.mfa.views.RecoveryCodes.get_unused_codes', return_value=['RC1', 'RC2', 'RC3'])
    @patch('jwt_allauth.mfa.views.TOTP.validate_code', return_value=True)
    def test_complete_mfa_flow(self, mock_validate_code, mock_get_unused_codes):
        """Test complete MFA setup and verification flow"""
        # Step 1: Setup - initiate TOTP
        resp = self.post(self.setup_url, data={}, status_code=200)
        self.assertIn('secret', resp)
        self.assertIn('provisioning_uri', resp)
        self.assertIn('qr_code', resp)

        # Step 2: Activate - confirm TOTP code (real activate, mocked validation + recovery codes)
        resp = self.post(
            self.activate_url,
            data={'code': '123456'},
            status_code=200
        )
        self.assertTrue(resp['success'])
        self.assertIn('recovery_codes', resp)
        self.assertEqual(resp['recovery_codes'], ['RC1', 'RC2', 'RC3'])

        # Step 3: List authenticators
        resp = self.get(self.authenticators_url, status_code=200)
        # TOTP + recovery codes authenticators should exist
        self.assertEqual(len(resp), 2)
        types = sorted([item['type'] for item in resp])
        self.assertEqual(types, ['recovery_codes', 'totp'])

    @patch('jwt_allauth.mfa.views.RecoveryCodes.get_unused_codes', return_value=['RC1'])
    @patch('jwt_allauth.mfa.views.TOTP.validate_code', return_value=True)
    def test_mfa_setup_and_deactivation_flow(self, mock_validate_code, mock_get_unused_codes):
        """Test MFA setup followed by deactivation"""
        # Setup
        self.post(self.setup_url, data={}, status_code=200)

        # Activate (real activate, mocked validation + recovery codes)
        self.post(
            self.activate_url,
            data={'code': '123456'},
            status_code=200
        )

        # Verify MFA is active
        resp = self.get(self.authenticators_url, status_code=200)
        # TOTP + recovery codes authenticators should exist
        self.assertEqual(len(resp), 2)
        types = sorted([item['type'] for item in resp])
        self.assertEqual(types, ['recovery_codes', 'totp'])

        # Deactivate
        resp = self.post(
            self.deactivate_url,
            data={'password': self.PASS},
            status_code=200
        )
        self.assertTrue(resp['success'])

        # Verify MFA is deactivated
        resp = self.get(self.authenticators_url, status_code=200)
        self.assertEqual(len(resp), 0)

    @patch('jwt_allauth.mfa.views.RecoveryCodes.get_unused_codes', return_value=['RC1'])
    @patch('jwt_allauth.mfa.views.TOTP.validate_code', return_value=True)
    def test_cannot_setup_mfa_twice(self, mock_validate_code, mock_get_unused_codes):
        """Test that user cannot setup MFA twice"""
        # First setup and activation
        self.post(self.setup_url, data={}, status_code=200)

        self.post(
            self.activate_url,
            data={'code': '123456'},
            status_code=200
        )

        # Try to setup again
        resp = self.post(self.setup_url, data={}, status_code=400)
        self.assertEqual(resp['detail'], 'TOTP already activated.')
