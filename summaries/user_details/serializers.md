## Location
`user_details.serializers`

## Purpose
Defines a serializer for user model data excluding password fields, providing read-only email and editable name fields for API responses.

## Dependencies
- **Internal**:
  - None
- **External**:
  - `django.contrib.auth` - Provides user model access via get_user_model()
  - `rest_framework` - Provides serializers.ModelSerializer base class

## Main structure

### Classes

#### `UserDetailsSerializer`

  - **Responsibility**: Serialize user model instances to JSON representation with specific field constraints
  - **Important attributes**:
    - `Meta.model`: Django User model class (dynamic via get_user_model())
    - `Meta.fields`: Tuple ('email', 'first_name', 'last_name') - defines serialized output fields
    - `Meta.read_only_fields`: Tuple ('email',) - prevents email modification through API
  - **Primary methods**:
    - Inherits all ModelSerializer methods (to_representation, to_internal_value, validate, etc.)

### Functions
None

### Global variables/constants
None

## Usage examples
```python
# Serialize user instance for API response
serializer = UserDetailsSerializer(user_instance)
serialized_data = serializer.data
```
