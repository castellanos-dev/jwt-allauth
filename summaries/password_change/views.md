## Location
`password_change.views`

## Purpose
Provides a Django REST Framework view for authenticated users to change their password securely.

## Dependencies
- **Internal**:
  - `jwt_allauth.app_settings` - Provides PasswordChangeSerializer for password validation
  - `jwt_allauth.utils` - Provides sensitive_post_parameters_m decorator for security
- **External**:
  - `django.contrib.auth` - User model management
  - `django.utils.translation` - Internationalization support
  - `rest_framework.generics` - GenericAPIView base class
  - `rest_framework.permissions` - IsAuthenticated permission class
  - `rest_framework.response` - Response object for API responses
  - `rest_framework.throttling` - UserRateThrottle for rate limiting

## Main structure

### Classes

#### `PasswordChangeView`

  - **Responsibility**: Handle password change requests from authenticated users with validation and security measures
  - **Important attributes**:
    - `serializer_class`: PasswordChangeSerializer, validates and processes password data
    - `permission_classes`: (IsAuthenticated,), restricts access to authenticated users only
    - `throttle_classes`: [UserRateThrottle], implements rate limiting
  - **Primary methods**:
    - `dispatch(*args, **kwargs)`: Wrapped with sensitive_post_parameters_m to protect sensitive data in logs
    - `post(request)`: Processes password change POST requests, validates data, saves new password, returns success response

## Usage examples
```python
# Client would typically POST to this endpoint with:
# {"new_password1": "newpass123", "new_password2": "newpass123"}
# Returns: {"detail": "New password has been saved."}
```

## Test criteria
- Verify authentication requirement (401 for unauthenticated requests)
- Test rate limiting behavior
- Validate password requirements through serializer
- Confirm sensitive parameters are properly masked
- Ensure successful password change updates user record
- Verify proper response format and internationalization
