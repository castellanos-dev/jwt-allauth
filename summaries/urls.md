## Location
`jwt_allauth.urls`

## Purpose
Defines URL routing for JWT authentication endpoints, including login, logout, password management, and user registration.

## Dependencies
- **Internal**:
  - `jwt_allauth.login.views` - Provides LoginView for user authentication
  - `jwt_allauth.logout.views` - Provides LogoutView and LogoutAllView for session termination
  - `jwt_allauth.password_change.views` - Provides PasswordChangeView for password updates
  - `jwt_allauth.password_reset.views` - Provides password reset functionality views
  - `jwt_allauth.token_refresh.views` - Provides TokenRefreshView for JWT token renewal
  - `jwt_allauth.user_details.views` - Provides UserDetailsView for user profile access
  - `jwt_allauth.registration.urls` - Provides registration-related URL patterns
- **External**:
  - `django` - Web framework for URL routing and view handling
  - `django.conf.settings` - Configuration access for conditional URL patterns

## Main structure

### Classes
*No classes defined in this file - contains URL pattern configuration*

### Functions
*No standalone functions defined in this file*

### Global variables/constants
- `urlpatterns`: List of URL patterns mapping endpoints to authentication views

## Usage examples
```python
# Accessing authentication endpoints
# POST /api/auth/login/ - User login
# POST /api/auth/refresh/ - Token refresh
# GET /api/auth/user/ - Retrieve user details (requires authentication)
# POST /api/auth/password/change/ - Change password (requires authentication)
```

## Test criteria
- Verify all URL patterns resolve to correct views
- Test authentication-required endpoints with valid/invalid tokens
- Validate password reset flow with different scenarios
- Check conditional URL patterns based on settings configuration
- Ensure proper HTTP methods are supported for each endpoint
