from jwt_allauth._importing import import_callable
from jwt_allauth import app_settings

RefreshToken = import_callable(app_settings.REFRESH_TOKEN_CLASS)
