# Module: registration

## Location
`jwt_allauth.registration`

## Module purpose
Handles user registration workflows with JWT authentication and allauth integration, including email verification, data validation, and token generation.

## Module structure
registration/
│
├── app_settings.py # Dynamically configures permission classes for registration endpoints
├── serializers.py # Provides DRF serializers for user registration with validation and cleaning
├── urls.py # Defines URL patterns for registration and email verification endpoints
├── views.py # Handles user registration requests with JWT token generation
└── __init__.py # Package initialization

## Relationships with other modules

  - **Dependencies**:
    - `allauth.account` - User account management and email verification workflows
    - `django.conf.settings` - Access application configuration
    - `rest_framework` - API serialization and view implementation
    - `jwt_allauth.tokens` - JWT token generation and management
    - `jwt_allauth.utils` - Utility functions and decorators
  - **Dependents**:
    - `Django URL configuration` - Uses registration URLs for authentication endpoints
    - `Client applications` - Consumes registration API endpoints for user creation

## Main interfaces

  - **Exported classes**:
    - `RegisterView` - Handles user registration requests and token generation
    - `RegisterSerializer` - Validates and processes user registration data
    - `VerifyEmailView` - Handles email verification requests
  - **Exported functions**:
    - `register_permission_classes()` - Builds permission classes tuple for registration views

## Important workflows
1. User registration: Validates input data, creates user account, generates JWT tokens
2. Email verification: Sends verification emails, handles confirmation links, updates user status
3. Permission configuration: Dynamically loads permission classes based on Django settings

## Implementation notes
- Uses allauth's email verification system with JWT token integration
- Dynamic permission class configuration allows customization via settings
- Atomic transactions ensure data consistency during user creation
- Sensitive data protection through decorators in view dispatch
- Template-based views for email verification confirmation pages
