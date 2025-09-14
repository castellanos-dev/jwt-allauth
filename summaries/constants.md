## Location
`project.constants`

## Purpose
Defines string constants used throughout the application for configuration keys, cookie names, and permission types.

## Dependencies
- **Internal**:
  - None
- **External**:
  - None

## Main structure

### Classes
None

### Functions
None

### Global variables/constants
  - `PASS_RESET`: String constant for password reset operations
  - `PASS_RESET_ACCESS`: String constant for password reset access operations
  - `TEMPLATE_PATHS`: Configuration key for JWT AllAuth template paths
  - `EMAIL_VERIFIED_REDIRECT`: Redirect configuration key for email verification
  - `PASSWORD_RESET_REDIRECT`: Redirect configuration key for password reset
  - `PASS_RESET_COOKIE`: Cookie name for password reset access tokens
  - `FOR_USER`: Key indicating user association
  - `ONE_TIME_PERMISSION`: Key for one-time permission grants
  - `REFRESH_TOKEN_COOKIE`: Cookie name for refresh tokens

## Usage examples
```python
# Accessing configuration constants
from constants import PASS_RESET_COOKIE, REFRESH_TOKEN_COOKIE

cookie_name = PASS_RESET_COOKIE  # 'password_reset_access_token'
refresh_cookie = REFRESH_TOKEN_COOKIE  # 'refresh_token'
```
