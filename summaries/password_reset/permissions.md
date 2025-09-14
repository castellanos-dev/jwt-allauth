## Location
`password_reset.permissions`

## Purpose
Defines a custom permission class for password reset endpoints that validates one-time JWT access tokens from cookies and sets up a temporary user context.

## Dependencies
- **Internal**:
  - `jwt_allauth.constants` - Provides constants for token claims and cookie names
  - `jwt_allauth.password_reset.models` - Provides SetPasswordTokenUser for temporary user representation
  - `jwt_allauth.tokens.app_settings` - Provides RefreshToken for token validation
- **External**:
  - `rest_framework.permissions` - Base class for custom permissions
  - `rest_framework_simplejwt` - Handles JWT token validation errors

## Main structure

### Classes

#### `ResetPasswordPermission`

  - **Responsibility**: Validates password reset requests by checking for a valid one-time JWT token in cookies and setting up authentication context
  - **Important attributes**:
    - None (inherits from BasePermission)
  - **Primary methods**:
    - `has_permission(request, view)`: Validates the presence and correctness of password reset token, sets request.user and request.auth if valid

### Functions
None

### Global variables/constants
None

## Usage examples
```python
# In DRF view
permission_classes = [ResetPasswordPermission]
# Valid request with correct cookie token will have request.user set to SetPasswordTokenUser
```

## Test criteria
- Should return False for authenticated users
- Should return False when no password reset cookie present
- Should return False for invalid/malformed tokens
- Should return False for tokens missing required claims
- Should return True and set user/auth for valid password reset tokens
- Should handle TokenError exceptions during token parsing
