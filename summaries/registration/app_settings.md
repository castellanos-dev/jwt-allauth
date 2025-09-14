## Location
`registration.app_settings`

## Purpose
Dynamically configures permission classes for JWT AllAuth registration endpoints based on Django settings.

## Dependencies
- **Internal**:
  - None
- **External**:
  - `django.conf.settings` - Access Django project settings
  - `rest_framework.permissions.AllowAny` - Default permission class
  - `jwt_allauth.utils.import_callable` - Utility to import callable classes from strings

## Main structure

### Functions
#### `register_permission_classes()`

  - **Purpose**: Builds a tuple of permission classes for registration views, starting with AllowAny and extending with custom classes from settings
  - **Parameters**:
    - None
  - **Returns**: `tuple` - Tuple of permission class objects

### Global variables/constants
  - None

## Usage examples
```python
# In Django settings.py
JWT_ALLAUTH_REGISTER_PERMISSION_CLASSES = [
    'myapp.permissions.CustomRegistrationPermission'
]

# Function returns: (AllowAny, CustomRegistrationPermission)
permission_classes = register_permission_classes()
```

## Test Criteria
- Verify returns tuple with AllowAny when no custom classes configured
- Verify imports and includes custom permission classes from settings
- Verify handles empty/missing settings attribute gracefully
- Test import_callable error handling for invalid class paths
