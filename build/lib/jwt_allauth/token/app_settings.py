from django.conf import settings

from jwt_allauth.token.tokens import RefreshToken as DefaultRefreshToken
from jwt_allauth.utils import import_callable

RefreshToken = import_callable(getattr(settings, 'JWT_ALLAUTH_REFRESH_TOKEN', DefaultRefreshToken))
