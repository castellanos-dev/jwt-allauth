## Location
`logout.serializers`

## Purpose
Handles secure logout by validating and removing refresh tokens from the whitelist to prevent reuse.

## Dependencies
- **Internal**:
  - `jwt_allauth.tokens.app_settings` - Provides RefreshToken class for token verification
  - `jwt_allauth.tokens.models` - Contains RefreshTokenWhitelistModel for token management
- **External**:
  - `django` - Web framework (ORM, security utilities)
  - `rest_framework` - API serialization framework
  - `rest_framework_simplejwt` - JWT token validation exceptions

## Main structure

### Classes

#### `RemoveRefreshTokenSerializer`

  - **Responsibility**: Validates refresh token ownership and removes it from the whitelist
  - **Important attributes**:
    - `refresh`: CharField - The refresh token string to be removed
    - `user`: CurrentUserDefault - Automatically provides the current user from request context
  - **Primary methods**:
    - `validate(attrs)`: Validates token ownership, checks whitelist presence, and deletes token
      - Parameters: `attrs` (Dict[str, Any]) - Input data containing refresh token
      - Returns: Empty dict on success
      - Raises: InvalidToken if validation fails

## Usage examples
```python
# Typical logout usage
serializer = RemoveRefreshTokenSerializer(data={'refresh': refresh_token})
serializer.is_valid(raise_exception=True)  # Validates and removes token
```
