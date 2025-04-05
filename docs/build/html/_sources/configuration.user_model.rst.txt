User Model
==========

Set the ``AUTH_USER_MODEL`` setting in the ``settings.py`` file:

.. code-block:: python

    AUTH_USER_MODEL = 'jwt_allauth.JAUser'

User profile details extension
------------------------------

The user model can be extended with the desired profile details. The new fields will be stored in a different table.

.. code-block:: python

    from django.db import models
    from django.contrib.auth.models import User
    from django.db.models.signals import post_save
    from django.dispatch import receiver

    class Profile(models.Model):
        user = models.OneToOneField(User, on_delete=models.CASCADE)
        # custom fields for user
        company_name = models.CharField(max_length=100)

        class Meta:
            app_label = 'users'

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()

To allow update user details within one request send to rest_auth.views.UserDetailsView view, create serializer like this:

.. code-block:: python

    from rest_framework import serializers
    from jwt_allauth.user_details.serializers import UserDetailsSerializer as JWTAllauthUserDetailsSerializer
    from users.models import Profile

    class UserDetailsSerializer(JWTAllauthUserDetailsSerializer):
        email = serializers.EmailField(read_only=True)
        first_name = serializers.CharField()
        last_name = serializers.CharField()

        company_name = serializers.CharField(
            source="profile.company_name",
            max_length=100
        )

        class Meta(JWTAllauthUserDetailsSerializer.Meta):
            model = Profile
            fields = JWTAllauthUserDetailsSerializer.Meta.fields + ('company_name',)
            read_only_fields = ('email',)

        def update(self, instance, validated_data):
            profile_data = validated_data.pop('profile', {})

            instance = super().update(instance, validated_data)

            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            return instance

And setup USER_DETAILS_SERIALIZER in django settings:

.. code-block:: python

    JWT_ALLAUTH_SERIALIZERS = {
        'USER_DETAILS_SERIALIZER': 'users.serializers.UserDetailsSerializer'
    }

User profile details modification
---------------------------------

This configuration substitutes the default users model, generating a new table.

.. note::

    This option is only recommended for new projects to prevent migration conflicts.

.. warning::

    :class:`~jwt_allauth.models.JAUser` must be inherited.

.. code-block:: python

    from jwt_allauth.models import JAUser
    from django.db import models

    class CustomUser(JAUser):
        company_name = models.CharField(max_length=100, blank=True, default='')

        class Meta:
            app_label = 'users'

Configuration of the serializers:

.. code-block:: python

    from allauth.account.internal.userkit import user_field
    from django.contrib.auth import get_user_model
    from jwt_allauth.registration.serializers import RegisterSerializer as JWTAllauthRegisterSerializer
    from jwt_allauth.user_details.serializers import UserDetailsSerializer as JWTAllauthUserDetailsSerializer
    from rest_framework import serializers

    class UserDetailsSerializer(JWTAllauthUserDetailsSerializer):
        company_name = serializers.CharField(max_length=100)

        class Meta(JWTAllauthUserDetailsSerializer.Meta):
            model = get_user_model()
            fields = JWTAllauthUserDetailsSerializer.Meta.fields + ('company_name',)
            read_only_fields = ('email',)

    class RegisterSerializer(JWTAllauthRegisterSerializer):
        company_name = serializers.CharField(required=True, write_only=True, max_length=100)

        def get_cleaned_data(self):
            cleaned_data = super().get_cleaned_data()
            cleaned_data['company_name'] = self.validated_data.get('company_name', '')
            return cleaned_data

        def custom_signup(self, request, user):
            user_field(user, "company_name", self.cleaned_data['company_name'])

And setup django settings:

.. code-block:: python

    AUTH_USER_MODEL = 'users.CustomUser'

    JWT_ALLAUTH_SERIALIZERS = {
        'REGISTER_SERIALIZER_SERIALIZER': 'users.serializers.RegisterSerializer'
        'USER_DETAILS_SERIALIZER': 'users.serializers.UserDetailsSerializer'
    }
