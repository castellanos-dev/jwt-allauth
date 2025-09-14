## Location
`project.module.exceptions`

## Purpose
Defines custom authentication-related exceptions for handling unverified email and incorrect credentials scenarios in a Django REST framework application.

## Dependencies
- **Internal**:
  - None
- **External**:
  - `rest_framework_simplejwt.exceptions` - Provides base AuthenticationFailed exception class
  - `django.utils.translation` - Used for internationalization of error messages
  - `rest_framework` - Provides HTTP status codes

## Main structure

### Classes

#### `NotVerifiedEmail`

  - **Responsibility**: Signals authentication failure due to unverified email address
  - **Important attributes**:
    - `status_code`: HTTP 401 Unauthorized status code
    - `default_detail`: Localized error message "User email is not verified"
    - `default_code`: Error code "email_not_verified"
  - **Primary methods**:
    - Inherits all methods from AuthenticationFailed base class

#### `IncorrectCredentials`

  - **Responsibility**: Signals authentication failure due to invalid credentials
  - **Important attributes**:
    - `status_code`: HTTP 401 Unauthorized status code
    - `default_detail`: Localized error message "Incorrect credentials"
    - `default_code`: Error code "incorrect_credentials"
  - **Primary methods**:
    - Inherits all methods from AuthenticationFailed base class

### Functions
None

### Global variables/constants
None

## Usage examples
```python
# Raising NotVerifiedEmail exception
raise NotVerifiedEmail()

# Raising IncorrectCredentials exception  
raise IncorrectCredentials()
```
