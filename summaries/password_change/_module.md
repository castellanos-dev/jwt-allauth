# Module: password_change

## Location
`password_change`

## Module purpose
Provides secure password change functionality for authenticated users in Django REST Framework, including validation, execution, and session/token management.

## Module structure
password_change/
│
├── serializers.py # Handles password change validation and execution with session/token cleanup
└── views.py # Provides API endpoint for password change requests with security measures

## Relationships with other modules

  - **Dependencies**:
    - `django.conf.settings` - Access application configuration settings
    - `django.contrib.auth` - User model and password management
    - `django.contrib.auth.forms.SetPasswordForm` - Validates and sets new passwords
    - `django.utils.translation` - Internationalization support
    - `rest_framework.serializers` - Base serializer functionality
    - `rest_framework.generics` - GenericAPIView base class
    - `rest_framework.permissions` - IsAuthenticated permission class
    - `rest_framework.response` - Response object for API responses
    - `rest_framework.throttling` - UserRateThrottle for rate limiting
    - `jwt_allauth.tokens.models` - Manages refresh token whitelist for session cleanup
    - `jwt_allauth.app_settings` - Provides PasswordChangeSerializer configuration
    - `jwt_allauth.utils` - Provides security decorators for sensitive data

## Main interfaces

  - **Exported classes**:
    - `PasswordChangeSerializer` - Validates password change requests and executes password updates
    - `PasswordChangeView` - Handles password change API endpoint with authentication and security

## Important workflows
1. User submits password change request with old and new passwords
2. Serializer validates old password (if enabled) and new password requirements
3. If validation passes, new password is saved to user account
4. Based on configuration, other user sessions may be logged out and refresh tokens cleaned up
5. Success response is returned to the client

## Implementation notes
- Uses Django's SetPasswordForm for robust password validation
- Supports configuration to disable old password validation for specific use cases
- Implements sensitive parameter masking to protect credentials in logs
- Includes rate limiting to prevent brute force attacks
- Handles JWT token cleanup when logging out other sessions
