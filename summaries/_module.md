# Module: jwt_allauth

## Location
`jwt_allauth`

## Module purpose
Provides JWT authentication integration with Django Allauth, offering secure token-based authentication with email verification, role-based permissions, and comprehensive authentication workflows.

## Module structure
jwt_allauth/
│
├── adapter.py # Custom AllAuth adapter for JWT-specific email handling and template customization
├── app_settings.py # Central configuration for customizable serializer imports with fallback defaults
├── apps.py # Django AppConfig for JWT Allauth integration and settings configuration
├── constants.py # String constants for configuration keys, cookie names, and permission types
├── exceptions.py # Custom authentication exceptions for unverified email and incorrect credentials
├── models.py # Custom User model with role-based access control and UserManager
├── permissions.py # Role-based permission classes for Django REST Framework using JWT claims
├── roles.py # Defines role constants for user privilege levels
├── test.py # Testing utilities with custom test client and base test case for JWT authentication
├── urls.py # URL routing for authentication endpoints (login, logout, password management, registration)
├── utils.py # Utility functions for authentication, user agent handling, and template configuration
└── __init__.py # Package initialization

## Relationships with other modules

  - **Dependencies**:
    - `django` - Core web framework functionality
    - `allauth` - Authentication and account management
    - `rest_framework_simplejwt` - JWT token implementation
    - `django_user_agents` - User agent parsing
  - **Dependents**:
    - `Django projects` - Provides authentication backend for web applications
    - `REST API consumers` - Offers JWT-based authentication endpoints

## Main interfaces

  - **Exported classes**:
    - `JWTAllAuthAdapter` - Custom account adapter for JWT-aware email confirmation
    - `JAUser` - Extended Django user model with role-based authorization
    - `JAClient` - Test client with automatic JWT authentication handling
    - `JATestCase` - Base test case with pre-configured authentication environment
    - `BasePermission` - Role-based permission class for DRF
  - **Exported functions**:
    - `allauth_authenticate()` - Authenticates user with email verification enforcement
    - `is_email_verified()` - Verifies if user has confirmed email address
    - `get_client_ip()` - Extracts client IP address from request
    - `get_user_agent()` - Decorator for adding user agent information to requests

## Important workflows
- User registration with email verification and JWT token issuance
- Login authentication with email/password validation and JWT token generation
- Password reset flow with secure token-based access
- Role-based access control using JWT claims for authorization
- Email confirmation workflows with custom template handling
- Token refresh mechanism for maintaining authenticated sessions

## Implementation notes
- Uses Django's AppConfig for automatic settings configuration and validation
- Implements custom User model with database-enforced role constraints
- Provides comprehensive testing utilities with pre-authenticated clients
- Supports template customization through configuration constants
- Integrates seamlessly with Django Allauth while adding JWT capabilities
- Includes role-based permission system that automatically grants staff/superuser access
