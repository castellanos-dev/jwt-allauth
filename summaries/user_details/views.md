## Location
`user_details.views`

## Purpose
Provides a Django REST framework view for retrieving and updating authenticated user details via GET and PATCH requests.

## Dependencies
- **Internal**:
  - `jwt_allauth.app_settings` - Provides UserDetailsSerializer for user model serialization
- **External**:
  - `django.contrib.auth` - User model access via get_user_model()
  - `rest_framework.generics` - RetrieveUpdateAPIView base class
  - `rest_framework.permissions` - IsAuthenticated permission class

## Main structure

### Classes

#### `UserDetailsView`

  - **Responsibility**: Handle authenticated user data retrieval and partial updates
  - **Important attributes**:
    - `serializer_class`: UserDetailsSerializer - Handles user model serialization/deserialization
    - `permission_classes`: (IsAuthenticated,) - Restricts access to authenticated users only
    - `http_method_names`: ['get', 'patch', 'head', 'options'] - Supported HTTP methods
  - **Primary methods**:
    - `get_object()`: Returns the currently authenticated user instance
    - `get_queryset()`: Returns empty queryset (workaround for django-rest-swagger compatibility)

## Usage examples
```python
# Retrieve current user details
GET /api/user/details/

# Update user first_name
PATCH /api/user/details/
Content-Type: application/json
{"first_name": "Updated Name"}
```
