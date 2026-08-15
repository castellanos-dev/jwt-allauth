"""
Request and response shapes of the social endpoints.

The credential serializers only check that the body is well formed. Whether a credential
is any good is the provider's answer to give, and it is asked for in
:mod:`jwt_allauth.social.flows`.
"""

from allauth.socialaccount.models import SocialAccount
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class SocialTokenSerializer(serializers.Serializer):
    """A credential the client obtained from the provider itself."""

    id_token = serializers.CharField(required=False, allow_blank=False, write_only=True)
    access_token = serializers.CharField(required=False, allow_blank=False, write_only=True)
    client_id = serializers.CharField(required=False, allow_blank=False, write_only=True)

    def validate(self, attrs):
        if not attrs.get('id_token') and not attrs.get('access_token'):
            raise serializers.ValidationError(_("Either an id_token or an access_token is required."))
        return attrs


class SocialCodeSerializer(serializers.Serializer):
    """An authorization code, to be exchanged with the provider server side."""

    code = serializers.CharField(write_only=True)
    callback_url = serializers.CharField(write_only=True)
    code_verifier = serializers.CharField(required=False, allow_blank=False, write_only=True)
    client_id = serializers.CharField(required=False, allow_blank=False, write_only=True)


class SocialAccountSerializer(serializers.ModelSerializer):
    """
    A provider connection, as its owner may see it.

    ``extra_data`` is deliberately absent: it is whatever the provider chose to send
    about the person, it is not needed to manage a connection, and an endpoint that
    returns it turns every provider's payload into part of this API.
    """

    class Meta:
        model = SocialAccount
        fields = ('id', 'provider', 'uid', 'last_login', 'date_joined')
        read_only_fields = fields


class SocialProviderSerializer(serializers.Serializer):
    """
    A provider the frontend may offer, with nothing secret in it.

    ``client_id`` is public by design -- it travels in every authorization request -- and
    the frontend needs it to build one. The app secret is never serialized.
    """

    id = serializers.CharField()
    name = serializers.CharField()
    client_id = serializers.CharField(allow_null=True)
