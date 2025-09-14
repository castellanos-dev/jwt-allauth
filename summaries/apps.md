## Location
`jwt_allauth.apps`

## Purpose
Django AppConfig for JWT Allauth integration, configuring Django settings for JWT authentication with Allauth constraints and defaults.

## Dependencies
- **Internal**:
  - `adapter.py` - Provides JWTAllAuthAdapter for account handling
- **External**:
  - `django` - Core Django framework
  - `allauth` - Authentication and account management
  - `rest_framework_simplejwt` - JWT token implementation

## Main structure

### Classes

#### `JWTAllauthAppConfig`

  - **Responsibility**: Configures Django settings for JWT+Allauth integration, validates required settings, and ensures proper authentication setup
  - **Important attributes**:
    - `name`: 'jwt_allauth' - App module name
    - `verbose_name`: "JWT Allauth" - Human-readable name
  - **Primary methods**:
    - `ready()`: Called when app is ready, configures all required settings and validates constraints

## Usage examples
```python
# App is automatically configured when Django starts
# Settings are validated and defaults are applied
```

## Key Configuration Points
- Enforces refresh token rotation (ROTATE_REFRESH_TOKENS=True)
- Disables token blacklisting (BLACKLIST_AFTER_ROTATION=False)
- Configures email-only login (ACCOUNT_LOGIN_METHODS={'email'})
- Sets default signup fields to email and passwords
- Configures JWT settings with secure defaults
- Sets up JWT authentication for REST framework
- Ensures proper authentication backends and middleware

## Test Criteria
- Verify settings validation raises ValueError for invalid configurations
- Test that all required settings are properly set with defaults
- Ensure JWT settings are correctly merged with existing SIMPLE_JWT settings
- Validate that authentication classes and backends are properly configured
- Test middleware inclusion and settings reload behavior
