## Location
`token_refresh.serializers`

## Purpose
Handles JWT token refresh operations with security validations and whitelist management.

## Dependencies
- **Internal**:
  - `jwt_allauth.tokens.app_settings` - Provides RefreshToken class for token operations
  - `jwt_allauth.tokens.models` - Contains RefreshTokenWhitelistModel for whitelist validation
  - `jwt_allauth.tokens.serializers` - Provides RefreshTokenWhitelistSerializer for whitelist serialization
  - `jwt_allauth.utils` - Provides is_email_verified utility for user verification
- **External**:
  - `rest_framework` - Django REST framework for serializers
  - `rest_framework_simplejwt` - Provides InvalidToken exception

## Main structure

### Classes

#### `TokenRefreshSerializer`

  - **Responsibility**: Validates refresh tokens, generates new access/refresh tokens, and manages token whitelist
  - **Important attributes**:
    - `refresh`: CharField - Input refresh token string
    - `access`: CharField (read-only) - Output access token string
    - `token_class`: RefreshToken class reference
  - **Primary methods**:
    - `validate(attrs)`: Validates refresh token, checks whitelist, generates new tokens, updates whitelist

## Usage examples
```python
serializer = TokenRefreshSerializer(data={'refresh': 'old_refresh_token'}, context={'user_agent': 'Mozilla/5.0'})
if serializer.is_valid():
    tokens = serializer.validated_data  # Returns {'access': 'new_access_token', 'refresh': 'new_refresh_token'}
```
