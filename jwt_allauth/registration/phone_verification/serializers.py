from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from jwt_allauth.models import PhoneAddress, PhoneConfirmation


class VerifyPhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        code = attrs.get('code')

        phone_address = PhoneAddress.objects.filter(
            phone_number=phone_number,
            verified=False,
        ).order_by('-pk').first()
        if phone_address is None:
            raise serializers.ValidationError(_("Phone number not found."))

        confirmation = PhoneConfirmation.objects.filter(
            phone_address=phone_address,
            key=code,
        ).order_by('-created').first()

        if not confirmation:
            raise serializers.ValidationError(_("Invalid code."))

        if confirmation.key_expired():
            raise serializers.ValidationError(_("Code expired."))

        attrs['confirmation'] = confirmation

        return attrs


class ResendPhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')

        phone_address = PhoneAddress.objects.filter(
            phone_number=phone_number,
            verified=False,
        ).order_by('-pk').first()
        if phone_address is None:
            raise serializers.ValidationError(_("Phone number not found."))

        last_confirmation = PhoneConfirmation.objects.filter(
            phone_address=phone_address,
        ).order_by('-created').first()

        if last_confirmation is not None and not last_confirmation.key_expired():
            raise serializers.ValidationError(_("A valid code already exists."))

        attrs['phone_address'] = phone_address
        return attrs
