# Module: project

## Location
`project`

## Module purpose
Project-level configuration and constants module providing shared constants and exception definitions used across the application.

## Module structure
project/
│
├── constants.py # Defines string constants for configuration keys, cookie names, and permission types
├── exceptions.py # Custom authentication-related exceptions for unverified email and incorrect credentials
└── __init__.py # Package initialization

## Relationships with other modules

  - **Dependencies**:
    - `rest_framework_simplejwt.exceptions` - Base exception classes
    - `django.utils.translation` - Internationalization support
  - **Dependents**:
    - `jwt_allauth` - Uses constants for configuration and exceptions for error handling
    - `Other project modules` - Provides shared constants and exception definitions

## Main interfaces

  - **Exported classes**:
    - `NotVerifiedEmail` - Signals authentication failure due to unverified email
    - `IncorrectCredentials` - Signals authentication failure due to invalid credentials
  - **Exported functions**:
    - None

## Important workflows
- Configuration management using shared constants for template paths, cookie names, and permission types
- Consistent error handling across authentication flows using custom exceptions
- Internationalization of error messages for user-facing authentication errors

## Implementation notes
- Constants are defined as simple string values for configuration keys and cookie names
- Custom exceptions inherit from DRF's AuthenticationFailed with specific status codes and error messages
- Exception messages are translatable using Django's internationalization framework
- Provides centralized configuration management for the entire application
