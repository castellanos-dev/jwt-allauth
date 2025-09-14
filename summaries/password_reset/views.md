## Location
`jwt_allauth.password_reset.views`

## Purpose
Handles password reset flow including email sending, token validation, and password setting with JWT token management.

## Dependencies
- **Internal**:
  - `jwt_allauth.app_settings` - Provides PasswordResetSerializer configuration
  - `jwt_allauth.constants` - Contains constants for token purposes and cookie names
  - `jwt_allauth.password_reset.permissions` - Provides ResetPasswordPermission for access control
  - `jwt_allauth.password_reset.serializers` - Provides SetPasswordSerializer for password validation
  - `jwt_allauth.tokens.app_settings` - Provides RefreshToken class
  - `jwt_allauth.tokens.models` - Provides GenericTokenModel and RefreshTokenWhitelistModel for token storage
  - `jwt_allauth.tokens.serializers` - Provides GenericTokenModelSerializer for token serialization
  - `jwt_allauth.tokens.tokens` - Provides GenericToken for token validation
  - `jwt_allauth.utils` - Provides decorators for user agent tracking and sensitive parameter handling
- **External**:
  - `django` - Web framework (settings, auth, HTTP handling)
  - `rest_framework` - API framework (views, responses, permissions)
  - `rest_framework_simplejwt` - JWT token handling (InvalidToken exception)

## Main structure

### Classes

#### `PasswordResetView`

  - **Responsibility**: Initiates password reset process by sending reset email
  - **Important attributes**:
    - `serializer_class`: PasswordResetSerializer - Handles email validation
    - `permission_classes`: (AllowAny,) - Allows unauthenticated access
    - `throttle_classes`: [AnonRateThrottle] - Rate limits anonymous requests
  - **Primary methods**:
    - `post(request)`: Validates email and sends password reset email, returns success message

#### `DefaultPasswordResetView`

  - **Responsibility**: Renders default password reset form template
  - **Important attributes**:
    - `permission_classes`: (AllowAny,) - Allows unauthenticated access
    - `template_name`: 'password/reset.html' - Template for reset form
  - **Primary methods**:
    - `get(request)`: Renders password reset form with validity check

#### `PasswordResetConfirmView`

  - **Responsibility**: Validates reset token and sets temporary access cookie
  - **Important attributes**:
    - `form_url`: URL for password reset form redirect
  - **Primary methods**:
    - `get(*_, **kwargs)`: Validates uidb64 and token, creates temporary access token and cookie
    - `get_user(uidb64)`: Static method to decode and retrieve user from base64 encoded user ID

#### `ResetPasswordView`

  - **Responsibility**: Handles actual password reset with token validation and session management
  - **Important attributes**:
    - `serializer_class`: SetPasswordSerializer - Validates new passwords
    - `permission_classes`: (ResetPasswordPermission,) - Validates temporary access token
    - `throttle_classes`: [UserRateThrottle] - Rate limits authenticated requests
  - **Primary methods**:
    - `dispatch(*args, **kwargs)`: Wraps super dispatch with sensitive parameter protection
    - `post(request)**: Validates single-use token, sets new password, manages sessions, returns JWT tokens

### Functions
#### `get_user(uidb64)`

  - **Purpose**: Decodes base64 user ID and retrieves user from database
  - **Parameters**:
    - `uidb64`: str - Base64 encoded user ID
  - **Returns**: User model instance or None if invalid

### Global variables/constants

  - None (Constants imported from jwt_allauth.constants)

## Usage examples
```python
# Password reset initiation
response = PasswordResetView().post(request_with_email)

# Password reset confirmation
response = PasswordResetConfirmView().get(request, uidb64='...', token='...')

# Password setting
response = ResetPasswordView().post(request_with_new_password)
```
