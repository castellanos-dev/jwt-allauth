# Module: logout

## Location
`jwt_allauth.logout`

## Module purpose
Provides secure user logout functionality for JWT-based authentication, including single session logout and logout from all devices by managing refresh token whitelist.

## Module structure
logout/
│
├── serializers.py # Handles refresh token validation and removal from whitelist
└── views.py # Provides API endpoints for logout operations

## Relationships with other modules

  - **Dependencies**:
    - `jwt_allauth.tokens` - For refresh token verification and whitelist management
    - `django` - Web framework and ORM
    - `rest_framework` - API serialization and view framework
    - `rest_framework_simplejwt` - JWT token validation and exceptions
  - **Dependents**:
    - Application API endpoints - Used by authentication system to provide logout functionality

## Main interfaces

  - **Exported classes**:
    - `RemoveRefreshTokenSerializer` - Validates refresh token ownership and removes from whitelist
    - `LogoutView` - Handles single session logout by invalidating current refresh token
    - `LogoutAllView` - Handles logout from all devices by removing all user's refresh tokens

## Important workflows
1. Single logout: User provides refresh token → Validate token ownership → Remove token from whitelist → Return success response
2. Logout all devices: Authenticated user request → Delete all refresh tokens for the user → Return success response

## Implementation notes
- Uses JWT refresh token whitelist for secure token invalidation
- Requires authenticated users for all operations
- Properly handles token validation errors with appropriate HTTP status codes
- Follows REST API patterns with POST requests for logout operations
