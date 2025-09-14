# Module: login

## Location
`login`

## Module purpose
Handles user authentication using JWT tokens with Django Allauth integration, providing both credential validation and token generation capabilities.

## Module structure
login/
│
├── serializers.py # Custom JWT token serializer for Allauth authentication
└── views.py # Authentication view with configurable token storage

## Relationships with other modules

  - **Dependencies**:
    - `jwt_allauth.tokens.app_settings` - Provides RefreshToken class for JWT generation
    - `jwt_allauth.utils` - Provides authentication utilities and decorators
    - `jwt_allauth.constants` - Provides configuration constants
    - `django` - Web framework for settings and database operations
    - `rest_framework` - API framework for serializers and views
    - `rest_framework_simplejwt` - JWT authentication infrastructure

  - **Dependents**:
    - Authentication clients - Consumes JWT tokens for API access
    - Frontend applications - Uses login endpoint for user authentication

## Main interfaces

  - **Exported classes**:
    - `LoginSerializer` - Validates credentials and generates JWT tokens with Allauth integration
    - `LoginView` - Handles authentication requests with configurable token storage

  - **Exported functions**:
    None

## Important workflows
1. User submits credentials (email/password) to login endpoint
2. LoginSerializer validates credentials using Allauth authentication
3. On successful authentication, JWT tokens (access and refresh) are generated
4. LoginView returns tokens either in response body or as HTTP cookies based on configuration
5. User's last login timestamp is updated if enabled in settings

## Implementation notes
- Supports both JSON response and cookie-based refresh token storage via JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE setting
- Uses atomic transactions to ensure data consistency during authentication
- Includes rate limiting (AnonRateThrottle) to prevent brute force attacks
- Integrates with Django Allauth for social authentication compatibility
- Handles inactive user accounts and authentication failures appropriately
