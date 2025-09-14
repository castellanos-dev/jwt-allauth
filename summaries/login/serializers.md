## Location
`login.serializers`

## Purpose
Custom JWT token serializer for user authentication that integrates Django Allauth authentication with SimpleJWT token generation.

## Dependencies
- **Internal**:
  - `jwt_allauth.tokens.app_settings` - Provides RefreshToken class for JWT token generation
  - `jwt_allauth.utils` - Provides allauth_authenticate function for Allauth-based authentication
- **External**:
  - `django` - Web framework (settings, auth models, database transactions)
  - `rest_framework` - API framework (exceptions)
  - `rest_framework_simplejwt` - JWT authentication (TokenObtainPairSerializer base, settings)

## Main structure

### Classes

#### `LoginSerializer`

  - **Responsibility**: Handles user authentication using Allauth, generates JWT tokens, and updates last login timestamp
  - **Important attributes**:
    - `token_class`: RefreshToken class for token generation
    - `username_field`: Authentication field (email by default from ACCOUNT_AUTHENTICATION_METHOD setting)
    - `user`: Authenticated user instance
  - **Primary methods**:
    - `get_token(user)`: Creates and returns refresh token for authenticated user
    - `validate(attrs)`: Validates credentials, authenticates user, generates tokens, updates last login

## Usage examples
```python
# Authentication with email and password
serializer = LoginSerializer(data={'email': 'user@example.com', 'password': 'secret'})
if serializer.is_valid():
    tokens = serializer.validated_data  # Contains refresh and access tokens
```

## Test criteria
- Validate successful authentication with correct credentials
- Test authentication failure with incorrect credentials
- Verify token generation (refresh and access tokens)
- Check last login timestamp update when enabled
- Test inactive user account rejection
- Validate transaction atomicity during authentication
- Test context request handling in authentication
