# Module: password_reset

## Location
`jwt_allauth.password_reset`

## Module purpose
Handles the complete password reset flow including email-based reset initiation, JWT token validation, and secure password setting with temporary access token management.

## Module structure
password_reset/
│
├── models.py # Extends TokenUser for password reset token user representation
├── serializers.py # Handles password reset requests and password setting operations
├── permissions.py # Validates one-time JWT access tokens for password reset endpoints
└── views.py # Implements password reset flow controllers and form handling

## Relationships with other modules

  - **Dependencies**:
    - `jwt_allauth.constants` - Provides constants for token claims and cookie names
    - `jwt_allauth.tokens` - Handles JWT token generation, validation, and storage
    - `rest_framework` - Provides API framework components and base classes
    - `rest_framework_simplejwt` - Offers JWT token handling infrastructure
    - `allauth.account` - Provides email validation and user management utilities
  - **Dependents**:
    - Application views and APIs that require password reset functionality

## Main interfaces

  - **Exported classes**:
    - `SetPasswordTokenUser` - Custom TokenUser extension for password reset token user representation
    - `PasswordResetSerializer` - Validates email and sends password reset emails
    - `SetPasswordSerializer` - Handles password setting without old password validation
    - `ResetPasswordPermission` - Validates one-time JWT access tokens for reset endpoints
    - `PasswordResetView` - Initiates password reset process
    - `ResetPasswordView` - Handles actual password reset with token validation

## Important workflows
1. Password reset initiation: User provides email → email validation → reset token generation → email dispatch
2. Token validation: User clicks reset link → token validation → temporary access cookie creation
3. Password setting: User submits new password → token validation → password update → session management

## Implementation notes
- Uses one-time JWT tokens stored in cookies for temporary access during password reset
- Integrates with Django's authentication system and allauth for email verification
- Implements rate limiting for both anonymous and authenticated reset requests
- Provides sensitive parameter protection during password reset operations
