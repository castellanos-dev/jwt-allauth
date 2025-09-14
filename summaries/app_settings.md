## Location
`jwt_allauth.app_settings`

## Purpose
Central configuration module for JWT Allauth serializers, providing customizable serializer imports with fallback defaults.

## Dependencies
- **Internal**:
  - `jwt_allauth.login.serializers` - Default login serializer implementation
  - `jwt_allauth.password_change.serializers` - Default password change serializer
  - `jwt_allauth.password_reset.serializers` - Default password reset serializer
  - `jwt_allauth.registration.serializers` - Default registration serializer
  - `jwt_allauth.user_details.serializers` - Default user details serializer
  - `jwt_allauth.utils` - Utility function for dynamic import
- **External**:
  - `django.conf.settings` - Django settings configuration

## Main structure

### Functions
#### `import_callable(import_path)`
  - **Purpose**: Dynamically imports and returns callable objects from string import paths
  - **Parameters**:
    - `import_path`: str, Python import path to the callable
  - **Returns**: Callable object

### Global variables/constants
  - `UserDetailsSerializer`: Configurable user details serializer, defaults to DefaultUserDetailsSerializer
  - `LoginSerializer`: Configurable login serializer, defaults to DefaultLoginSerializer
  - `PasswordResetSerializer`: Configurable password reset serializer, defaults to DefaultPasswordResetSerializer
  - `PasswordChangeSerializer`: Configurable password change serializer, defaults to DefaultPasswordChangeSerializer
  - `RegisterSerializer`: Configurable registration serializer, defaults to DefaultRegisterSerializer

## Usage examples
```python
# Access configured serializer
from jwt_allauth.app_settings import UserDetailsSerializer
serializer = UserDetailsSerializer(user_instance)
```
