## Location
`jwt_allauth.token_refresh.views`

## Purpose
Handles JWT token refresh operations with configurable storage (cookie vs. request body) and user agent tracking.

## Dependencies
- **Internal**:
  - `token_refresh.serializers` - Provides custom token refresh validation logic
  - `utils` - Provides user agent extraction and formatting utilities
  - `constants` - Provides refresh token cookie name constant
- **External**:
  - `django` - Framework for web application infrastructure
  - `rest_framework` - API framework for request/response handling
  - `rest_framework_simplejwt` - JWT token management and validation

## Main structure

### Classes

#### `TokenRefreshView`

  - **Responsibility**: Processes token refresh requests, validates tokens, and returns new access tokens with optional refresh token handling
  - **Important attributes**:
    - `serializer_class`: TokenRefreshSerializer - Handles token validation and refresh
    - `throttle_classes`: [UserRateThrottle] - Limits request rate per user
  - **Primary methods**:
    - `post(request: Request, *args, **kwargs) -> Response`: Processes POST requests for token refresh, extracts refresh token from cookie or body based on configuration, validates, and returns new tokens

## Usage examples
```python
# Client sends refresh token in cookie (default config)
response = client.post('/token/refresh/', cookies={'refresh_token': 'valid_refresh_token'})
# Returns: {'access': 'new_access_token'} with refresh token set as HTTP-only cookie

# Client sends refresh token in request body
response = client.post('/token/refresh/', {'refresh': 'valid_refresh_token'})
# Returns: {'access': 'new_access_token', 'refresh': 'new_refresh_token'}
```

## Suggested test criteria
- Token refresh with valid cookie-based refresh token
- Token refresh with valid body-based refresh token
- Token refresh with invalid/expired token (should raise InvalidToken)
- Rate limiting behavior with multiple requests
- Cookie settings (httponly, secure, samesite) based on DEBUG mode
- Configuration toggle between cookie and body token storage
- User agent context passing to serializer
