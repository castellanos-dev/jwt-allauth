## Location
`jwt_allauth.tokens.tokens`

## Purpose
Provides custom JWT token classes for authentication and authorization, extending Django REST framework's SimpleJWT with session tracking, user roles, and token whitelisting capabilities.

## Dependencies
- **Internal**:
  - `roles.py` - Defines role constants (STAFF_CODE, SUPER_USER_CODE)
  - `tokens/models.py` - Provides GenericTokenModel for token storage
  - `tokens/serializers.py` - Provides serializers for token validation and storage
  - `utils.py` - Provides user_agent_dict utility function
- **External**:
  - `django.contrib.auth.tokens` - PasswordResetTokenGenerator base class
  - `rest_framework.exceptions` - ValidationError for serializer validation
  - `rest_framework_simplejwt` - Default JWT token implementation and exceptions
  - `hashlib` - Token hashing for security
  - `uuid` - Session ID generation

## Main structure

### Classes

#### `RefreshToken`

  - **Responsibility**: Extends SimpleJWT RefreshToken with session tracking, user role inclusion, and database whitelisting
  - **Important attributes**:
    - `payload`: Dict containing JWT claims including custom session and role fields
  - **Primary methods**:
    - `set_session(id_=None)`: Sets unique session identifier in token payload
    - `set_user_role(user)`: Sets user role in token payload
    - `for_user(cls, user, request=None, enabled=True)`: Creates token for user with session tracking and database storage

#### `GenericToken`

  - **Responsibility**: Extends Django's PasswordResetTokenGenerator for generic purpose tokens with database tracking and automatic cleanup
  - **Important attributes**:
    - `purpose`: String identifying the token's intended use case
    - `request`: HTTP request object for user agent context
  - **Primary methods**:
    - `make_token(user)`: Creates and stores hashed token in database, removes previous tokens for same purpose
    - `check_token(user, token)`: Validates token against database and removes it upon successful validation

## Usage examples
```python
# Create refresh token with session tracking
refresh = RefreshToken.for_user(user, request)
access_token = str(refresh.access_token)

# Create generic token for email verification
token_generator = GenericToken('email_verification', request)
token = token_generator.make_token(user)
# Later verify the token
is_valid = token_generator.check_token(user, token)
```
