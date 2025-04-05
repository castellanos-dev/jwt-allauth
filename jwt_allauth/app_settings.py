from django.conf import settings

from jwt_allauth.login.serializers import LoginSerializer as DefaultLoginSerializer
from jwt_allauth.password_change.serializers import PasswordChangeSerializer as DefaultPasswordChangeSerializer
from jwt_allauth.password_reset.serializers import PasswordResetSerializer as DefaultPasswordResetSerializer
from jwt_allauth.registration.serializers import RegisterSerializer as DefaultRegisterSerializer
from jwt_allauth.user_details.serializers import UserDetailsSerializer as DefaultUserDetailsSerializer
from jwt_allauth.utils import import_callable

serializers = getattr(settings, 'JWT_ALLAUTH_SERIALIZERS', {})

UserDetailsSerializer = import_callable(serializers.get('USER_DETAILS_SERIALIZER', DefaultUserDetailsSerializer))

LoginSerializer = import_callable(serializers.get('LOGIN_SERIALIZER', DefaultLoginSerializer))

PasswordResetSerializer = import_callable(serializers.get('PASSWORD_RESET_SERIALIZER', DefaultPasswordResetSerializer))

PasswordChangeSerializer = import_callable(
    serializers.get('PASSWORD_CHANGE_SERIALIZER', DefaultPasswordChangeSerializer)
)

RegisterSerializer = import_callable(serializers.get('REGISTER_SERIALIZER', DefaultRegisterSerializer))
