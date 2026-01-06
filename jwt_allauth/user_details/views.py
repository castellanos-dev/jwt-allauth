from django.contrib.auth import get_user_model
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from jwt_allauth import app_settings


class UserDetailsView(RetrieveUpdateAPIView):
    """
    Reads and updates UserModel fields
    Accepts GET, PATCH methods.

    Default accepted fields: username, first_name, last_name
    Default display fields: pk, username, email, first_name, last_name
    Read-only fields: pk, email

    Returns UserModel fields.
    """
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        return app_settings.UserDetailsSerializer

    def get_object(self):
        return get_user_model().objects.get(id=self.request.user.id)

    def get_queryset(self):
        """
        Adding this method since it is sometimes called when using
        django-rest-swagger
        https://github.com/Tivix/django-rest-auth/issues/275
        """
        return get_user_model().objects.none()
