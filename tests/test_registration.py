from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from rest_framework import status
from jwt_allauth.constants import REFRESH_TOKEN_COOKIE
from jwt_allauth.tokens.models import RefreshTokenWhitelistModel

from .mixins import TestsMixin


class RegistrationTests(TestsMixin):
    """
    Case #1:
    - user profile: defined
    - custom registration: backend defined
    """

    REGISTRATION_EMAIL = 'registration_email@email.com'
    # data without user profile
    REGISTRATION_DATA = {
        "email": REGISTRATION_EMAIL,
        "password1": TestsMixin.PASS,
        "password2": TestsMixin.PASS,
        "first_name": TestsMixin.FIRST_NAME,
        "last_name": TestsMixin.LAST_NAME
    }

    REGISTRATION_LOGIN_DATA = {
        "email": REGISTRATION_EMAIL,
        "password": TestsMixin.PASS
    }

    def setUp(self):
        self.init()

    def _login(self):
        resp = self.post(self.login_url, data=self.REGISTRATION_LOGIN_DATA, status_code=status.HTTP_200_OK)
        self.assertIn('access', resp.keys())
        self.assertNotIn('refresh', resp.keys())
        # Check that cookie was set
        response = self.client.post(
            self.login_url,
            data=self.LOGIN_PAYLOAD,
            format='json'
        )
        self.assertIn(REFRESH_TOKEN_COOKIE, response.cookies)
        self.assertTrue(response.cookies[REFRESH_TOKEN_COOKIE]['httponly'])
        self.token = resp['access']

    def test_registration_no_payload(self):
        resp = self.post(self.register_url, data={}, status_code=400)
        self.assertEqual(resp['email'][0], u'This field is required.')
        self.assertEqual(resp['password1'][0], u'This field is required.')
        self.assertEqual(resp['password2'][0], u'This field is required.')
        self.assertEqual(resp['first_name'][0], u'This field is required.')
        self.assertEqual(resp['last_name'][0], u'This field is required.')

    def test_registration_methods_not_allowed(self):
        resp = self.get(self.register_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "GET" not allowed.')
        resp = self.put(self.register_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PUT" not allowed.')
        resp = self.patch(self.register_url, data={}, status_code=405)
        self.assertEqual(resp['detail'], u'Method "PATCH" not allowed.')
        resp = self.delete(self.register_url, status_code=405)
        self.assertEqual(resp['detail'], u'Method "DELETE" not allowed.')

    def test_registration_invalid_password(self):
        data = self.REGISTRATION_DATA.copy()
        data['password1'] = 'password'
        data['password2'] = 'password'
        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertEqual(resp['password1'][0], 'This password is too common.')

        data['password1'] = 'short$'
        data['password2'] = 'short$'
        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertEqual(resp['password1'][0], 'This password is too short. It must contain at least 8 characters.')

    def test_registration_invalid_email(self):
        data = self.REGISTRATION_DATA.copy()
        data['email'] = 'invalid_email'

        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertEqual(resp['email'][0], u'Enter a valid email address.')
        self.assertFalse(get_user_model().objects.filter(email=data['email']).exists())

    def test_registration_different_passwords(self):
        data = self.REGISTRATION_DATA.copy()
        data['password2'] = 'different_password'

        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertEqual(resp['non_field_errors'][0], u"The two password fields didn't match.")
        self.assertFalse(get_user_model().objects.filter(email=data['email']).exists())

    def test_email_not_verified_repeated_registration(self):
        mail_count = len(mail.outbox)
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertEqual(len(mail.outbox), mail_count + 1)
        # Works since the email is not verified
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertEqual(len(mail.outbox), mail_count + 2)
        # The superseded sign-up is removed as a whole: no account is left behind
        # holding the address it no longer owns.
        self.assertEqual(get_user_model().objects.filter(email=self.REGISTRATION_EMAIL).count(), 1)
        self.assertEqual(EmailAddress.objects.filter(email=self.REGISTRATION_EMAIL).count(), 1)

    def test_pending_registration_survives_an_invalid_attempt(self):
        """
        A registration that is rejected must not take a pending sign-up with it.
        """
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        pending = get_user_model().objects.get(email=self.REGISTRATION_EMAIL)

        data = self.REGISTRATION_DATA.copy()
        data['password1'] = data['password2'] = 'short$'
        self.post(self.register_url, data=data, status_code=400)

        self.assertTrue(get_user_model().objects.filter(id=pending.id).exists())
        self.assertTrue(EmailAddress.objects.filter(user=pending, email=self.REGISTRATION_EMAIL).exists())

    def test_unverified_address_of_an_established_account_is_not_reclaimable(self):
        """
        Registering an address that an established account is still confirming must
        not delete it: only sign-ups that nobody ever confirmed can be superseded.
        """
        secondary = 'secondary@email.com'
        address = EmailAddress.objects.create(user=self.USER, email=secondary, verified=False)

        data = self.REGISTRATION_DATA.copy()
        data['email'] = secondary
        self.post(self.register_url, data=data, status_code=201)

        address.refresh_from_db()
        self.assertEqual(address.user_id, self.USER.id)
        self.assertFalse(get_user_model().objects.filter(email=secondary).exists())

    @override_settings(EMAIL_VERIFICATION=False)
    def test_email_case_insensitive_registration(self):
        data = self.REGISTRATION_DATA.copy()
        data['email'] = 'TestCase@Email.com'
        self.post(self.register_url, data=data, status_code=201)
        # Intento de registro con mismo email en diferente formato
        data['email'] = 'testcase@email.com'
        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertIn('email', resp)
        self.assertEqual(resp['email'][0], 'A user is already registered with this e-mail address.')

    @override_settings(ACCOUNT_PREVENT_ENUMERATION=False)
    def test_registration_existing_email(self):
        data = self.REGISTRATION_DATA.copy()
        data['email'] = self.EMAIL
        self.assertEqual(get_user_model().objects.filter(email=self.EMAIL).count(), 1)

        email_object = EmailAddress.objects.get(user=self.USER, email=self.EMAIL)
        self.assertTrue(email_object.verified)

        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertEqual(resp['email'][0], u'A user is already registered with this e-mail address.')
        self.assertEqual(get_user_model().objects.filter(email=self.EMAIL).count(), 1)

        email_object.verified = False
        email_object.save()

        self.post(self.register_url, data=data, status_code=201)
        self.assertEqual(get_user_model().objects.filter(email=self.EMAIL).count(), 1)

    def test_registration_existing_email_is_not_disclosed(self):
        """
        An anonymous caller must not be able to tell a taken address from a free one.
        """
        mail.outbox = []
        taken = self.REGISTRATION_DATA.copy()
        taken['email'] = self.EMAIL
        self.assertTrue(EmailAddress.objects.get(user=self.USER, email=self.EMAIL).verified)

        user_count = get_user_model().objects.count()
        taken_resp = self.post(self.register_url, data=taken, status_code=201)

        # Nothing is created, and the owner of the address is warned instead of
        # receiving a confirmation link somebody else could follow.
        self.assertEqual(get_user_model().objects.count(), user_count)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.EMAIL])
        self.assertIn('already have an account', mail.outbox[0].subject)
        self.assertNotIn('/registration/verification/', self._mail_body(mail.outbox[0]))

        # ... and the response is the very same one a fresh address gets.
        free_resp = self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertEqual(taken_resp, free_resp)
        self.assertEqual(taken_resp, {'detail': u'Verification e-mail sent.'})

    def test_pending_registration_of_another_account_is_not_disclosed(self):
        """
        The same holds for an address that an established account has not confirmed
        yet: it is taken, and saying so would leak it just the same.
        """
        secondary = 'secondary@email.com'
        EmailAddress.objects.create(user=self.USER, email=secondary, verified=False)

        data = self.REGISTRATION_DATA.copy()
        data['email'] = secondary
        mail.outbox = []
        resp = self.post(self.register_url, data=data, status_code=201)

        self.assertEqual(resp, {'detail': u'Verification e-mail sent.'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn('/registration/verification/', self._mail_body(mail.outbox[0]))

    @override_settings(EMAIL_VERIFICATION=False)
    def test_registration_existing_email_without_verification(self):
        """
        Without mandatory verification a sign-up answers with session tokens, which
        cannot be faked for somebody else's address: the conflict is reported.
        """
        data = self.REGISTRATION_DATA.copy()
        data['email'] = self.EMAIL
        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertEqual(resp['email'][0], u'A user is already registered with this e-mail address.')

    @staticmethod
    def _mail_body(message):
        return ' '.join([message.body] + [alt for alt, _ in getattr(message, 'alternatives', [])])

    def test_registration(self):
        user_count = get_user_model().objects.all().count()

        resp = self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        # No refresh token while address conflicts are hidden: it could not be minted
        # for an address that is already in use, so it would give the answer away.
        self.assertNotIn('refresh', resp)
        self.assertNotIn('access', resp)
        self.assertEqual(resp['detail'], u'Verification e-mail sent.')
        self.assertEqual(get_user_model().objects.all().count(), user_count + 1)

        self.get(self.user_url, status_code=401)

        new_user = get_user_model().objects.latest('id')
        email_object = EmailAddress.objects.get(user=new_user, email=new_user.email)
        self.assertFalse(email_object.verified)
        email_object.verified = True
        email_object.save()

        self.assertEqual(new_user.email, self.REGISTRATION_DATA['email'])

        self._login()
        self.get(self.user_url, status_code=200)
        self._logout()

    @override_settings(ACCOUNT_PREVENT_ENUMERATION=False)
    def test_registration_returns_refresh_token_without_enumeration_prevention(self):
        """
        Opting out of enumeration prevention restores the refresh token issued at
        registration, which becomes usable once the address is verified.
        """
        resp = self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertIn('refresh', resp)
        self.assertEqual(resp['detail'], u'Verification e-mail sent.')

        # Disabled until the address is verified.
        self.client.cookies[REFRESH_TOKEN_COOKIE] = resp['refresh']
        self.post(self.refresh_url, data={}, status_code=401)

        new_user = get_user_model().objects.latest('id')
        self.assertTrue(RefreshTokenWhitelistModel.objects.filter(user=new_user, enabled=False).exists())
        email_object = EmailAddress.objects.get(user=new_user, email=new_user.email)
        email_object.verified = True
        email_object.save()
        RefreshTokenWhitelistModel.objects.filter(user=new_user).update(enabled=True)

        self.post(self.refresh_url, data={}, status_code=200)

    @override_settings(EMAIL_VERIFICATION=False)
    def test_registration_no_email_verification(self):
        user_count = get_user_model().objects.all().count()

        resp = self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertIn('refresh', resp)
        self.assertIn('access', resp)
        self.assertEqual(get_user_model().objects.all().count(), user_count + 1)

        self.get(self.user_url, status_code=401)
        self.token = resp['access']
        self.get(self.user_url, status_code=200)
        self._logout()

        new_user = get_user_model().objects.latest('id')
        email_object = EmailAddress.objects.get(user=new_user, email=new_user.email)
        self.assertTrue(email_object.verified)

        self.assertEqual(new_user.email, self.REGISTRATION_DATA['email'])

        self._login()
        self.get(self.user_url, status_code=200)
        self._logout()

    def test_registration_missing_first_name(self):
        data = self.REGISTRATION_DATA.copy()
        del data['first_name']
        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertIn('first_name', resp)
        self.assertEqual(resp['first_name'][0], 'This field is required.')

    def test_registration_missing_last_name(self):
        data = self.REGISTRATION_DATA.copy()
        del data['last_name']
        resp = self.post(self.register_url, data=data, status_code=400)
        self.assertIn('last_name', resp)
        self.assertEqual(resp['last_name'][0], 'This field is required.')

    def test_user_profile_created(self):
        user_count = get_user_model().objects.count()
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        new_user = get_user_model().objects.latest('id')
        # Verifies user creation
        self.assertTrue(hasattr(new_user, 'email'))
        self.assertEqual(new_user.email, self.REGISTRATION_EMAIL)
        self.assertEqual(user_count + 1, get_user_model().objects.count())

    def test_cannot_login_without_verification(self):
        mail_count = len(mail.outbox)
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        self.assertEqual(len(mail.outbox), mail_count + 1)
        # Intento de login sin verificar
        resp = self.post(self.login_url, data=self.REGISTRATION_LOGIN_DATA, status_code=401)
        self.assertIn('detail', resp)
        self.assertEqual(resp['detail'], "User email is not verified")

    def test_registration_saves_names_correctly(self):
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        new_user = get_user_model().objects.latest('id')
        self.assertEqual(new_user.first_name, self.FIRST_NAME)
        self.assertEqual(new_user.last_name, self.LAST_NAME)

    def test_user_active_status_after_verification(self):
        self.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)
        new_user = get_user_model().objects.latest('id')
        self.assertTrue(new_user.is_active)

        email = EmailAddress.objects.get(user=new_user)
        email.verified = True
        email.save()
        new_user.refresh_from_db()
        self.assertTrue(new_user.is_active)
