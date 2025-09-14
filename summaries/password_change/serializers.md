## Location
`password_change.serializers`

## Purpose
Handles password change validation and execution for Django REST Framework, including old password verification, new password validation, and session/token management.

## Dependencies
- **Internal**:
  - `jwt_allauth.tokens.models` - Used to manage refresh token whitelist when logging out other sessions
- **External**:
  - `django.conf.settings` - Access application configuration settings
  - `django.contrib.auth.forms.SetPasswordForm` - Validates and sets new passwords
  - `django.utils.translation` - Internationalization support
  - `rest_framework.serializers` - Base serializer functionality

## Main structure

### Classes

#### `PasswordChangeSerializer`

  - **Responsibility**: Validates password change requests and executes password updates with proper session/token cleanup
  - **Important attributes**:
    - `old_password_field_enabled`: bool, Controls whether old password validation is required
    - `logout_on_password_change`: bool, Determines if other sessions should be logged out
    - `request`: HttpRequest, The current request object from context
    - `user`: User, The authenticated user from the request
  - **Primary methods**:
    - `validate_old_password(value)`: Validates that the provided old password matches the user's current password
    - `validate(attrs)`: Validates new password fields using Django's SetPasswordForm
    - `save()`: Saves the new password and handles session/token management based on configuration

## Usage examples
```python
# Typical password change usage
serializer = PasswordChangeSerializer(data=request_data, context={'request': request})
if serializer.is_valid():
    serializer.save()
    return Response({'detail': 'Password updated successfully'})
```

## Test Criteria
- Validate old password correctly rejects invalid passwords
- Validate new password requirements through SetPasswordForm
- Test both logout and session preservation scenarios
- Verify token whitelist cleanup when logout enabled
- Test configuration variations (old password field disabled)
- Ensure proper error messages for validation failures
