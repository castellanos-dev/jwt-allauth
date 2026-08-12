import threading
import time
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase

from jwt_allauth.token_refresh.serializers import TokenRefreshSerializer
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel
from jwt_allauth.tokens.serializers import RefreshTokenWhitelistSerializer
from jwt_allauth.tokens.tokens import RefreshToken
from jwt_allauth.utils import user_sessions_lock

TIMEOUT = 15


class SessionRevocationConcurrencyTests(TransactionTestCase):
    """
    A revocation must not be overtaken by a rotation that commits after it started.

    Rotation deletes the whitelist row it consumes and inserts the successor. Under
    ``READ COMMITTED`` a revocation that started first does not see that successor: it
    reports success and the session stays open. Both sides take the lock on the user, so
    the revocation runs against the committed outcome of the rotation.

    Needs real commits from more than one connection, so it is a ``TransactionTestCase``,
    and a backend that actually locks rows -- SQLite serializes writers instead and the
    interleaving cannot be reproduced there.
    """

    def setUp(self):
        if not connection.features.has_select_for_update:
            self.skipTest('backend without SELECT ... FOR UPDATE')
        self.user = get_user_model().objects.create_user(
            'racer', email='racer@demo.com', password='A-1_strong'
        )
        EmailAddress.objects.create(user=self.user, email='racer@demo.com', verified=True, primary=True)
        self.refresh_token = RefreshToken.for_user(self.user)

    def _rotate(self, inserted, release, errors):
        """Rotate the token, holding the transaction open once the successor is written."""
        original_save = RefreshTokenWhitelistSerializer.save

        def paused_save(serializer, **kwargs):
            result = original_save(serializer, **kwargs)
            inserted.set()
            release.wait(timeout=TIMEOUT)
            return result

        try:
            with patch.object(RefreshTokenWhitelistSerializer, 'save', paused_save):
                serializer = TokenRefreshSerializer(data={'refresh': str(self.refresh_token)}, context={})
                serializer.is_valid(raise_exception=True)
        except Exception as exc:  # surfaced in the main thread
            errors.append(exc)
        finally:
            inserted.set()
            connection.close()

    def _revoke_all(self, inserted, errors):
        """Close every session of the user, the way ``LogoutAllView`` does."""
        try:
            inserted.wait(timeout=TIMEOUT)
            with user_sessions_lock(self.user.pk):
                RefreshTokenWhitelistModel.objects.filter(user=self.user).delete()
        except Exception as exc:
            errors.append(exc)
        finally:
            connection.close()

    def test_revocation_does_not_miss_a_rotation_committing_after_it(self):
        inserted, release, errors = threading.Event(), threading.Event(), []

        rotation = threading.Thread(target=self._rotate, args=(inserted, release, errors))
        revocation = threading.Thread(target=self._revoke_all, args=(inserted, errors))

        rotation.start()
        revocation.start()
        # The successor is written but not committed; give the revocation time to reach
        # the lock and block on it before the rotation is allowed to commit.
        self.assertTrue(inserted.wait(timeout=TIMEOUT))
        time.sleep(0.5)
        release.set()

        rotation.join(TIMEOUT)
        revocation.join(TIMEOUT)

        self.assertEqual(errors, [])
        self.assertFalse(rotation.is_alive())
        self.assertFalse(revocation.is_alive())
        self.assertFalse(
            RefreshTokenWhitelistModel.objects.filter(user=self.user).exists(),
            'the rotated session survived the revocation of every session of the user',
        )
