# Module: registration/email_verification

## Location
`registration.email_verification`

## Module purpose
Handles email verification functionality for user registration, including validation of verification keys and processing verification requests to confirm user emails and enable refresh tokens.

## Module structure
registration/email_verification/
│
├── serializers.py # Defines serializer for email verification request validation
└── views.py # Handles email verification via GET requests and redirects

## Relationships with other modules

  - **Dependencies**:
    - `rest_framework` - Provides serializers and APIView base class
    - `allauth.account.views` - Base ConfirmEmailView functionality
    - `django` - HTTP responses, URL reversal, and settings
    - `jwt_allauth.constants` - Provides EMAIL_VERIFIED_REDIRECT setting
    - `jwt_allauth.tokens.models` - Contains RefreshTokenWhitelistModel for token management
  - **Dependents**:
    - None specified in provided summaries

## Main interfaces

  - **Exported classes**:
    - `VerifyEmailSerializer` - Validates and deserializes email verification requests containing verification keys
    - `VerifyEmailView` - Processes email verification via GET requests, enables refresh tokens, and redirects users
  - **Exported functions**:
    - None

## Important workflows
1. User receives email verification link
2. User clicks link, making GET request to VerifyEmailView
3. VerifyEmailSerializer validates the verification key
4. If valid, email is confirmed and associated refresh token is enabled
5. User is redirected to success page

## Implementation notes
- Uses GET requests exclusively for email verification (POST returns 405 Method Not Allowed)
- Publicly accessible (AllowAny permission)
- Integrates Django REST Framework with allauth email confirmation functionality
- Requires proper URL routing to connect verification links to VerifyEmailView
