## Location
`tokens.models`

## Purpose
Defines database models for token management, including base token tracking, refresh token whitelisting, and generic purpose tokens with device/user context.

## Dependencies
- **Internal**:
  - `jwt_allauth.utils` - Used to dynamically import token model class from settings
- **External**:
  - `django.db.models` - ORM for database model definitions
  - `django.conf.settings` - Access to project settings
  - `django.utils.translation` - Internationalization support
  - `rest_framework.authtoken.models` - Default token model fallback

## Main structure

### Classes

#### `BaseToken`

  - **Responsibility**: Abstract base model for tracking token metadata including device information, browser details, and creation timestamp
  - **Important attributes**:
    - `id`: BigAutoField, primary key
    - `created`: DateTimeField, auto-generated creation timestamp
    - `ip`: GenericIPAddressField, client IP address
    - Various device detection fields (is_mobile, is_tablet, is_pc, is_bot)
    - Browser/OS/device metadata fields

#### `AbstractRefreshToken`

  - **Responsibility**: Abstract model extending BaseToken with JWT-specific fields (jti, enabled status, session identifier)
  - **Important attributes**:
    - `jti`: CharField, JWT ID claim (required)
    - `enabled`: BooleanField, token activation status
    - `session`: CharField, session identifier (required)

#### `RefreshTokenWhitelistModel`

  - **Responsibility**: Concrete model for storing whitelisted refresh tokens with user association
  - **Important attributes**:
    - `user`: ForeignKey to AUTH_USER_MODEL, token owner with CASCADE delete

#### `GenericTokenModel`

  - **Responsibility**: Concrete model for storing generic purpose tokens with customizable purpose field
  - **Important attributes**:
    - `user`: ForeignKey to AUTH_USER_MODEL, token owner with CASCADE delete
    - `token`: CharField, token value (required)
    - `purpose`: CharField, token purpose identifier (required)

### Global variables/constants

  - `TokenModel`: Dynamically imported token model class from REST_AUTH_TOKEN_MODEL setting or DefaultTokenModel fallback

## Usage examples
```python
# Creating a whitelisted refresh token
refresh_token = RefreshTokenWhitelistModel.objects.create(
    user=user_instance,
    jti="unique_jti_string",
    session="session_id_123",
    ip="192.168.1.1",
    is_mobile=True
)

# Creating a generic purpose token
generic_token = GenericTokenModel.objects.create(
    user=user_instance,
    token="random_token_string",
    purpose="password_reset",
    browser="Chrome",
    os="Windows"
)
```
