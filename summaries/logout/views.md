## Location
`jwt_allauth.logout.views`

## Purpose
Provides API endpoints for user logout functionality, including single session logout and logout from all devices.

## Dependencies
- **Internal**:
  - `jwt_allauth.logout.serializers` - Used for token validation and removal during logout
  - `jwt_allauth.tokens.models` - Used to access and manipulate refresh token whitelist records
- **External**:
  - `django` - Web framework
  - `rest_framework` - API framework for view classes and responses
  - `rest_framework_simplejwt` - JWT token handling and validation

## Main structure

### Classes

#### `LogoutView`

  - **Responsibility**: Handles single session logout by invalidating the current refresh token
  - **Important attributes**:
    - `permission_classes`: (IsAuthenticated,) - Requires authenticated users
  - **Primary methods**:
    - `post(request)`: Processes logout POST request
    - `logout(request)`: Static method that validates and removes refresh token

#### `LogoutAllView`

  - **Responsibility**: Handles logout from all devices by removing all refresh tokens for the user
  - **Important attributes**:
    - `permission_classes`: (IsAuthenticated,) - Requires authenticated users
  - **Primary methods**:
    - `post(request)`: Processes logout all POST request
    - `logout(request)`: Static method that deletes all refresh tokens for the user

### Functions
None

### Global variables/constants
None

## Usage examples
```python
# Single logout
response = client.post('/logout/', {}, HTTP_AUTHORIZATION='Bearer <token>')

# Logout from all devices
response = client.post('/logout/all/', {}, HTTP_AUTHORIZATION='Bearer <token>')
```

## Test criteria
- Verify authenticated users can logout successfully
- Test unauthorized access returns proper status
- Validate token removal from whitelist for LogoutView
- Confirm all tokens are removed for LogoutAllView
- Test error handling for invalid tokens
- Verify proper HTTP status codes and response messages
