from rest_framework import serializers

from jwt_allauth.token.models import RefreshTokenWhitelistModel, GenericTokenModel


class RefreshTokenWhitelistSerializer(serializers.ModelSerializer):
    """
    User model w/o password
    """

    class Meta:
        model = RefreshTokenWhitelistModel
        exclude = ('id',)


class GenericTokenModelSerializer(serializers.ModelSerializer):
    """
    User model w/o password
    """

    class Meta:
        model = GenericTokenModel
        exclude = ('id',)
