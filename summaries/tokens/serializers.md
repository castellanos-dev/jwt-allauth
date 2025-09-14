## Location
`jwt_allauth.tokens.serializers`

## Purpose
Provides Django REST Framework serializers for token models to handle JSON serialization/deserialization for API operations.

## Dependencies
- **Internal**:
  - `tokens.models` - Provides RefreshTokenWhitelistModel and GenericTokenModel for serializer field mapping
- **External**:
  - `rest_framework.serializers` - Base serializer classes and field handling

## Main structure

### Classes

#### `RefreshTokenWhitelistSerializer`

  - **Responsibility**: Serialize/deserialize RefreshTokenWhitelistModel instances for API operations
  - **Important attributes**:
    - `Meta.model`: RefreshTokenWhitelistModel - The model class being serialized
    - `Meta.exclude`: ('id',) - Excludes the id field from serialization
  - **Primary methods**:
    - Inherits all ModelSerializer methods (create, update, validate, etc.)

#### `GenericTokenModelSerializer`

  - **Responsibility**: Serialize/deserialize GenericTokenModel instances for API operations
  - **Important attributes**:
    - `Meta.model`: GenericTokenModel - The model class being serialized
    - `Meta.exclude`: ('id',) - Excludes the id field from serialization
  - **Primary methods**:
    - Inherits all ModelSerializer methods (create, update, validate, etc.)

### Functions
*No standalone functions*

### Global variables/constants
*No global variables/constants*

## Usage examples
```python
# Serialize a refresh token instance
serializer = RefreshTokenWhitelistSerializer(refresh_token_instance)
serialized_data = serializer.data

# Deserialize data to create/update token
serializer = GenericTokenModelSerializer(data=request_data)
if serializer.is_valid():
    token_instance = serializer.save()
```
