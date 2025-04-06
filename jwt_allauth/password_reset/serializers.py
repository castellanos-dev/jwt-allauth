from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.sites.requests import RequestSite
from rest_framework import serializers

from jwt_allauth.constants import PASS_RESET
from jwt_allauth.password_change.serializers import PasswordChangeSerializer
from jwt_allauth.tokens.tokens import GenericToken
from jwt_allauth.utils import get_template_path


class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset e-mail.
    """
    email = serializers.EmailField()

    password_reset_form_class = PasswordResetForm

    def get_email_options(self):
        """Override this method to change default e-mail options"""
        return {}

    def validate_email(self, value):
        value = get_adapter().clean_email(value)
        # Create PasswordResetForm with the serializer
        self.reset_form = self.password_reset_form_class(data=self.initial_data)
        if not self.reset_form.is_valid():
            raise serializers.ValidationError(self.reset_form.errors)

        return value

    def save(self):
        request = self.context.get('request')

        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL'),
            'request': request,
            'domain_override': RequestSite(request).domain,
            'token_generator': GenericToken(request=request, purpose=PASS_RESET),
            'subject_template_name': get_template_path('PASS_RESET_SUBJECT', 'email/password/reset_email_subject.txt'),
            'html_email_template_name': get_template_path('PASS_RESET_EMAIL', 'email/password/reset_email_message.html'),
        }

        opts.update(self.get_email_options())
        # Check if the email is verified
        if EmailAddress.objects.filter(email=self.validated_data['email'], verified=True).count() > 0:
            self.reset_form.save(**opts)

class SetPasswordSerializer(PasswordChangeSerializer):
    old_password = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_password_field_enabled = False
        self.logout_on_password_change = False

        if 'old_password' in self.fields:
            self.fields.pop('old_password')

    def validate_old_password(self, value):
        pass
