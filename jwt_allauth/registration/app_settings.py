from rest_framework.permissions import AllowAny
from jwt_allauth._importing import import_callable
from jwt_allauth import app_settings


def register_permission_classes():
    permission_classes = [AllowAny, ]
    for klass in app_settings.REGISTER_PERMISSION_CLASSES:
        permission_classes.append(import_callable(klass))
    return tuple(permission_classes)
