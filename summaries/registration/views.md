## Location
`jwt_allauth.registration.views`

## Purpose
Handles user registration with JWT token generation and allauth integration for email verification workflows.

## Dependencies
- **Internal**:
  - `jwt_allauth.registration.app_settings` - Retrieves permission classes for registration view
  - `jwt_allauth.app_settings` - Provides RegisterSerializer for user registration
  - `jwt_allauth.tokens.app_settings` - Provides RefreshToken class for JWT generation
  - `jwt_allauth.tokens.models` - Provides TokenModel reference
  - `jwt_allauth.utils` - Provides sensitive_post_parameters_m decorator and get_user_agent decorator
- **External**:
  - `allauth.account` - Handles email verification settings and signup completion
  - `django` - Framework core and settings management
  - `rest_framework` - API view implementation and response handling

## Main structure

### Classes

#### `RegisterView`

  - **Responsibility**: Handles user registration requests, creates users, generates JWT tokens, and manages email verification workflow
  - **Important attributes**:
    - `serializer_class`: RegisterSerializer, validates and processes registration data
    - `permission_classes`: Dynamic permission classes from app settings
    - `token_model`: TokenModel, reference to token model class
    - `jwt_token`: RefreshToken, class for generating JWT refresh tokens
  - **Primary methods**:
    - `dispatch(*args, **kwargs)`: Wrapped with sensitive_post_parameters_m to protect sensitive data
    - `get_response_data(token)`: Static method that formats response based on email verification setting
    - `create(request, *args, **kwargs)`: Main registration endpoint, validates data, creates user, returns tokens
    - `perform_create(serializer)`: Creates user, generates tokens, completes allauth signup process

### Functions
#### `get_response_data(token)`

  - **Purpose**: Formats the response data structure based on email verification configuration
  - **Parameters**:
    - `token`: RefreshToken instance containing JWT tokens
  - **Returns**: Dictionary with appropriate response structure (either verification message or token pair)

### Global variables/constants

  - `logger`: logging.Logger instance for registration-related logging

## Usage examples
```python
# Typical registration request
response = client.post('/api/register/', {
    'email': 'user@example.com',
    'password': 'securepassword123',
    'password_confirm': 'securepassword123'
})
# Returns either verification message with refresh token or both refresh/access tokens
```

## Test criteria
- Registration with valid data returns 201 status and appropriate token response
- Email verification setting controls response format
- Invalid registration data returns appropriate validation errors
- Sensitive parameters are properly protected in dispatch
- User agent information is captured in create method
- allauth signup completion is properly triggered
- JWT tokens are generated correctly for the created user
