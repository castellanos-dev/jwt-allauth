User Model
==========

JWT Allauth works with any user model. What the user model decides is where the ``role``
claim comes from, and there are three ways to answer that -- pick the one that matches
where the project is.

New project: use the shipped model
----------------------------------

``JAUser`` is Django's ``AbstractUser`` with the role field already on it. Set it before
the first migration:

.. code-block:: python

    AUTH_USER_MODEL = 'jwt_allauth.JAUser'

Existing project: add the field to the model you have
-----------------------------------------------------

``AUTH_USER_MODEL`` cannot realistically be swapped once a project has migrations, so
adopting ``JAUser`` is off the table. :class:`~jwt_allauth.models.RoleMixin` adds the
same field to the user model already in place -- one field, one migration:

.. code-block:: python

    from django.contrib.auth.models import AbstractUser
    from jwt_allauth.models import RoleMixin

    class MyUser(RoleMixin, AbstractUser):
        pass

.. warning::

    Existing rows take the default role, :data:`~jwt_allauth.roles.USER_CODE`. That is
    correct for every account except the staff ones, which were reading as
    :data:`~jwt_allauth.roles.STAFF_CODE` through the fallback below and would silently
    drop to a regular user on the next login. Backfill them in the migration that adds
    the field:

    .. code-block:: python

        from django.db import migrations
        from jwt_allauth.roles import STAFF_CODE, SUPER_USER_CODE

        def backfill_roles(apps, schema_editor):
            user = apps.get_model('myapp', 'MyUser')
            user.objects.filter(is_staff=True).update(role=STAFF_CODE)
            user.objects.filter(is_staff=False, is_superuser=True).update(role=SUPER_USER_CODE)

        class Migration(migrations.Migration):
            dependencies = [('myapp', '0012_previous')]
            operations = [
                migrations.AddField(
                    model_name='myuser',
                    name='role',
                    field=models.PositiveSmallIntegerField(default=0),
                ),
                migrations.RunPython(backfill_roles, migrations.RunPython.noop),
            ]

To keep the role and the staff flags in step from then on, use the manager too:

.. code-block:: python

    from jwt_allauth.models import RoleMixin, UserManager

    class MyUser(RoleMixin, AbstractUser):
        objects = UserManager()

``JAUser`` also declares two check constraints tying ``is_staff`` and ``is_superuser`` to
their role codes at the database level. ``RoleMixin`` deliberately leaves them out:
adding a check constraint to a populated table fails while a single staff row still holds
the default role, which would make the migration unrunnable on exactly the projects the
mixin is for. Declare them next to the backfill if the guarantee is wanted.

Any user model: no field at all
-------------------------------

Doing nothing is a supported configuration. With no ``role`` field, the claim is derived
from the staff flags Django gives every user model:

=================================  ===================================================
Account                            Role claim
=================================  ===================================================
``is_staff``                       :data:`~jwt_allauth.roles.STAFF_CODE` (1000)
``is_superuser`` without staff     :data:`~jwt_allauth.roles.SUPER_USER_CODE` (900)
anything else                      :data:`~jwt_allauth.roles.USER_CODE` (0)
=================================  ===================================================

That is enough for :class:`~jwt_allauth.permissions.BasePermission`, which grants staff
and superusers access on top of the roles a class accepts, and for the admin-managed
registration endpoint, which is gated on those same two codes. What it cannot express is
roles of the project's own -- ``accepted_roles = [700]`` will never match anything -- and
adding ``RoleMixin`` is what unlocks those.

The mapping is exactly the one ``JAUser`` enforces, so adding the field later leaves the
accounts that already existed where they were.

.. note::

    A ``role`` exposed as a property rather than a field is read like a stored one, which
    is the way to derive the claim from something the project already has (a group, a
    column on a profile) without a new field. It is read-only: the admin-managed
    registration endpoint drops its ``role`` input when there is no field to write to.

.. note::

    A **nullable** ``role`` field left empty falls back to the staff flags as well, row by
    row. ``JAUser`` and ``RoleMixin`` both declare the field ``null=False`` with a default,
    so this only concerns a project that declared its own; there, an account with the
    column empty carries the role its flags imply rather than a ``null`` claim, which is
    what such an account had been carrying before |release| and which matched no
    permission class at all -- staff included.

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
