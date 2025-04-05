from django.conf import settings

from rest_framework.permissions import AllowAny
from jwt_allauth.utils import import_callable


def register_permission_classes():
    permission_classes = [AllowAny, ]
    for klass in getattr(settings, 'JWT_ALLAUTH_REGISTER_PERMISSION_CLASSES', tuple()):
        permission_classes.append(import_callable(klass))
    return tuple(permission_classes)
