## Location
`jwt_allauth.utils`

## Purpose
Provides utility functions for authentication, user agent handling, and template configuration in a Django allauth + JWT integration.

## Dependencies
- **Internal**:
  - `jwt_allauth.constants` - For template path configuration constants
  - `jwt_allauth.exceptions` - For custom authentication exceptions
- **External**:
  - `django` - Web framework core
  - `allauth` - Authentication adapter integration
  - `django_user_agents` - User agent parsing
  - `rest_framework_simplejwt` - JWT token validation
  - `six` - Python 2/3 compatibility

## Main structure

### Functions
#### `import_callable(path_or_callable)`
  - **Purpose**: Converts Python path strings to callable objects or returns callable inputs
  - **Parameters**:
    - `path_or_callable`: str or callable - Python path string or callable object
  - **Returns**: callable - Resolved callable object

#### `get_client_ip(request)`
  - **Purpose**: Extracts client IP address from request metadata with X-Forwarded-For priority
  - **Parameters**:
    - `request`: HttpRequest - Django request object
  - **Returns**: str - Client IP address or None

#### `get_user_agent(f)`
  - **Purpose**: Decorator that adds user agent and IP information to request objects
  - **Parameters**:
    - `f`: function - View method to decorate
  - **Returns**: function - Decorated view method

#### `user_agent_dict(request)`
  - **Purpose**: Generates detailed dictionary of user agent information including browser, OS, device, and network details
  - **Parameters**:
    - `request`: HttpRequest - Django request object
  - **Returns**: dict - Structured user agent details or empty dict

#### `get_template_path(constant, default)`
  - **Purpose**: Retrieves template paths from Django settings using configuration constants
  - **Parameters**:
    - `constant`: str - Key to look up in TEMPLATE_PATHS setting
    - `default`: str - Default path if not found
  - **Returns**: str - Configured template path or default

#### `is_email_verified(user, raise_exception=False)`
  - **Purpose**: Verifies if a user has confirmed email address, optionally raising exception
  - **Parameters**:
    - `user`: User - User object to check
    - `raise_exception`: bool - Whether to raise NotVerifiedEmail if unverified
  - **Returns**: bool - True if verified, False otherwise

#### `allauth_authenticate(**kwargs)`
  - **Purpose**: Authenticates user using allauth's adapter with email verification enforcement
  - **Parameters**:
    - `**kwargs`: Authentication credentials (username/email + password)
  - **Returns**: User - Authenticated user object

#### `load_user(f)`
  - **Purpose**: Decorator that loads complete user object from database for stateless JWT authentication
  - **Parameters**:
    - `f`: function - View method to decorate
  - **Returns**: function - Decorated view method

### Global variables/constants
  - `sensitive_post_parameters_m`: Method decorator for protecting password parameters in POST requests

## Usage examples
```python
# Authenticate user with email verification
user = allauth_authenticate(username='test', password='secret')

# Check email verification status
verified = is_email_verified(user, raise_exception=True)

# Get client IP from request
ip_address = get_client_ip(request)

# Load complete user object in JWT view
@load_user
def my_view(self, request):
    return Response({'user_email': request.user.email})
```
