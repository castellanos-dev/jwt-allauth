# Module: tokens

## Location
`jwt_allauth.tokens`

## Module purpose
Provides comprehensive JWT token management including token generation, validation, database storage, and serialization for authentication and authorization workflows.

## Module structure
tokens/
│
├── app_settings.py # Configures and imports refresh token class from Django settings
├── models.py # Defines database models for token tracking and whitelisting
├── serializers.py # Provides DRF serializers for token model API operations
├── tokens.py # Implements custom JWT token classes with session tracking and role management
└── __init__.py # Module initialization and exports

## Relationships with other modules

  - **Dependencies**:
    - `django` - Configuration system and ORM foundation
    - `rest_framework` - Serializer base classes and authentication framework
    - `rest_framework_simplejwt` - Base JWT token implementation
    - `jwt_allauth.utils` - Utility functions for dynamic imports and user agent parsing
    - `jwt_allauth.roles` - Role constants for user permission management
  - **Dependents**:
    - Authentication modules - Uses token classes for JWT authentication flows
    - API endpoints - Uses serializers and models for token management operations

## Main interfaces

  - **Exported classes**:
    - `RefreshToken` - Custom JWT refresh token with session tracking and role inclusion
    - `GenericToken` - Generic purpose token generator with database storage
    - `RefreshTokenWhitelistModel` - Database model for whitelisted refresh tokens
    - `GenericTokenModel` - Database model for generic purpose tokens
    - `RefreshTokenWhitelistSerializer` - Serializer for refresh token API operations
    - `GenericTokenModelSerializer` - Serializer for generic token API operations

## Important workflows
- JWT token generation with session tracking and user role inclusion
- Refresh token whitelisting in database for revocation control
- Generic token creation and validation for various application purposes
- Token serialization/deserialization for REST API operations
- Dynamic token class loading from Django settings for customization

## Implementation notes
- Uses dynamic import system to allow custom token class configuration via settings
- Implements database-backed token storage for enhanced security and management
- Extends SimpleJWT with additional session and role capabilities
- Provides abstract base models for extensible token tracking
- Includes comprehensive device and browser metadata collection
