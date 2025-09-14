## Location
`login.views`

## Purpose
Handles user authentication via JWT tokens, supporting both JSON response and cookie-based refresh token storage based on configuration.

## Dependencies
- **Internal**:
  - `jwt_allauth.app_settings` - Provides LoginSerializer for credential validation
  - `jwt_allauth.utils` - Provides decorators for sensitive parameter handling and user agent extraction
  - `jwt_allauth.constants` - Provides REFRESH_TOKEN_COOKIE constant
- **External**:
  - `django` - Web framework (settings access)
  - `rest_framework` - API framework (Request, Response, status codes)
  - `rest_framework_simplejwt` - JWT token generation and validation

## Main structure

### Classes

#### `LoginView`

  - **Responsibility**: Authenticates users and returns JWT tokens, with configurable refresh token storage (response body vs cookie)
  - **Important attributes**:
    - `serializer_class`: LoginSerializer - Handles credential validation and token generation
    - `throttle_classes`: [AnonRateThrottle] - Prevents brute force attacks on login
  - **Primary methods**:
    - `post(request: Request, *args, **kwargs) -> Response`: Processes login request, validates credentials, returns tokens based on configuration

### Functions
None

### Global variables/constants
None

## Usage examples
```python
# Client login request
response = client.post('/login/', {'username': 'user', 'password': 'pass'})
# Returns access token in body, refresh token in cookie (default)
# Or access+refresh tokens in body if JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE=False
```
