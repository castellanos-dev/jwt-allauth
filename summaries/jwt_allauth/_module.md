# Module: jwt_allauth

## Location
`jwt_allauth`

## Module purpose
Core authentication module providing JWT integration with Django Allauth, handling user authentication, registration, password management, and role-based access control.

## Module structure
jwt_allauth/
│
├── adapter.py # Custom AllAuth adapter for JWT-specific email handling and template customization
├── app_settings.py # Central configuration for customizable serializer imports with fallback defaults
├── apps.py # Django AppConfig for JWT Allauth integration and settings configuration
├── constants.py # String constants for configuration keys, cookie names, and permission types
├── exceptions.py # Custom authentication exceptions for unverified email and incorrect credentials
├── models.py # Custom User model and UserManager with role-based access control
├── permissions.py # Role-based permission classes for Django REST Framework using JWT claims
├── roles.py # Role-based access control constants for user privilege levels
├── test.py # Testing utilities with custom test client and base test case with JWT authentication
├── urls.py # URL routing for JWT authentication endpoints
└── utils.py # Utility functions for authentication, user agent handling, and template configuration

## Relationships with other modules

  - **Dependencies**:
    - `allauth` - Authentication and account management integration
    - `rest_framework_simplejwt` - JWT token implementation and validation
    - `django` - Core web framework functionality
    - `django_user_agents` - User agent parsing for enhanced authentication
  - **Dependents**:
    - `Django project` - Provides authentication backend for the entire application
    - `REST API endpoints` - Secures API access with JWT authentication and role-based permissions

## Main interfaces

  - **Exported classes**:
    - `JWTAllAuthAdapter` - Custom account adapter for JWT-aware email confirmation
    - `JAUser` - Extended Django user model with role-based authorization
    - `UserManager` - Custom user creation with automatic role assignment
    - `JAClient` - Test client with automatic JWT authentication handling
    - `JATestCase` - Base test case with pre-configured authenticated environment
    - `BasePermission` - Role-based permission class with staff/superuser auto-grant
  - **Exported functions**:
    - `allauth_authenticate()` - Authenticates user with email verification enforcement
    - `is_email_verified()` - Verifies if user has confirmed email address
    - `get_client_ip()` - Extracts client IP address from request metadata
    - `get_user_agent()` - Decorator for adding user agent information to requests
    - `import_callable()` - Converts Python path strings to callable objects

## Important workflows
- User registration with email verification and JWT token generation
- Login authentication with JWT token issuance and role validation
- Password reset flow with secure token-based access control
- Email confirmation with custom template paths and JWT context
- Role-based access control for API endpoints using JWT claims
- Automated testing with pre-authenticated client and user setup

## Implementation notes
- Uses Django settings for customizable serializer imports with fallback defaults
- Enforces email verification for authentication with custom exception handling
- Implements role-based constraints at database level for staff/superuser validation
- Provides decorators for automatic user loading and user agent enhancement
- Configures secure JWT settings with refresh token rotation and proper authentication backends
