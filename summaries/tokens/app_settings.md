## Location
`tokens.app_settings`

## Purpose
Configures and imports the refresh token class for JWT authentication, allowing customization through Django settings.

## Dependencies
- **Internal**:
  - `tokens.tokens` - Provides the default refresh token implementation
  - `utils` - Provides import_callable utility for dynamic class loading
- **External**:
  - `django` - Uses Django settings system for configuration
  - `jwt_allauth` - JWT authentication library framework

## Main structure

### Global variables/constants
  - `RefreshToken`: Dynamically imported refresh token class (either custom from settings or default)

## Usage examples
```python
# Using the configured refresh token class
token = RefreshToken.for_user(user)
```

## Test criteria
- Verify RefreshToken imports DefaultRefreshToken when no custom setting
- Test custom token class loading via JWT_ALLAUTH_REFRESH_TOKEN setting
- Ensure imported class maintains expected refresh token interface
- Validate proper error handling for invalid import paths
