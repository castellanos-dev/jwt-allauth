## Location
`registration.email_verification.views`

## Purpose
Handles email verification via GET requests, enabling refresh tokens upon confirmation and redirecting users after successful verification.

## Dependencies
- **Internal**:
  - `jwt_allauth.constants` - Provides EMAIL_VERIFIED_REDIRECT setting constant
  - `jwt_allauth.tokens.models` - Contains RefreshTokenWhitelistModel for token management
  - `jwt_allauth.registration.email_verification.serializers` - Provides VerifyEmailSerializer for validation
- **External**:
  - `allauth.account.views` - Base ConfirmEmailView functionality
  - `django` - HTTP responses, URL reversal, and settings
  - `rest_framework` - APIView base class and AllowAny permission

## Main structure

### Classes

#### `VerifyEmailView`

  - **Responsibility**: Combines Django REST Framework APIView with allauth email confirmation to verify emails via GET requests, enable associated refresh tokens, and redirect users
  - **Important attributes**:
    - `permission_classes`: (tuple) Set to AllowAny for public access
    - `allowed_methods`: (tuple) Restricts to GET requests only
  - **Primary methods**:
    - `get(request, *args, **kwargs)`: Processes email verification, enables refresh token, confirms email, and redirects
    - `post(request, *args, **kwargs)`: Returns HTTP 405 Method Not Allowed
    - `get_serializer(*args, **kwargs)`: Returns VerifyEmailSerializer instance

### Functions
None

### Global variables/constants
None

## Usage examples
```python
# Typically accessed via URL route pointing to VerifyEmailView.as_view()
# GET request to verification link automatically triggers the flow
```
