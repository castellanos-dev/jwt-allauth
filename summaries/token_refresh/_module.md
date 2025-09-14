# Module: token_refresh

## Location
`jwt_allauth.token_refresh`

## Module purpose
Handles JWT token refresh operations with security validations, whitelist management, and configurable storage (cookie vs. request body) with user agent tracking.

## Module structure
token_refresh/
│
├── serializers.py # Handles JWT token refresh validation, whitelist management, and token generation
└── views.py # Processes token refresh requests with configurable storage and user agent tracking

## Relationships with other modules

  - **Dependencies**:
    - `jwt_allauth.tokens` - Provides RefreshToken class, whitelist models, and token utilities
    - `jwt_allauth.utils` - Provides user verification utilities
    - `rest_framework` - Django REST framework for serializers and views
    - `rest_framework_simplejwt` - JWT token management and validation
    - `django` - Web application framework infrastructure
  - **Dependents**:
    - API clients - Consumes token refresh endpoints to obtain new access tokens

## Main interfaces

  - **Exported classes**:
    - `TokenRefreshSerializer` - Validates refresh tokens, generates new tokens, and manages token whitelist
    - `TokenRefreshView` - Processes token refresh requests with configurable storage and rate limiting

## Important workflows
1. Token refresh validation: Validates incoming refresh tokens against whitelist and expiration
2. Token generation: Creates new access and refresh tokens upon successful validation
3. Storage configuration: Supports both cookie-based and request body-based token storage
4. User agent tracking: Captures and logs user agent information for security purposes
5. Whitelist management: Updates refresh token whitelist during refresh operations

## Implementation notes
- Uses configurable approach for token storage (cookie vs. body) based on application settings
- Implements rate limiting with UserRateThrottle to prevent abuse
- Maintains refresh token whitelist for enhanced security and token revocation
- Extracts user agent from request context for security logging and validation
- Handles both cookie-based authentication (HTTP-only cookies) and traditional token exchange
