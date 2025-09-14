# Module: user_details

## Location
`user_details`

## Module purpose
Provides user profile management functionality for authenticated users, including retrieval and updating of user details through REST API endpoints.

## Module structure
user_details/
│
├── serializers.py # Defines serializer for user model data with read-only email and editable name fields
└── views.py # Provides API view for retrieving and updating authenticated user details

## Relationships with other modules

  - **Dependencies**:
    - `django.contrib.auth` - Provides user model access via get_user_model()
    - `rest_framework` - Provides serializers and API view base classes
    - `rest_framework.permissions` - Provides IsAuthenticated permission class
    - `jwt_allauth.app_settings` - Provides UserDetailsSerializer for user model serialization

## Main interfaces

  - **Exported classes**:
    - `UserDetailsSerializer` - Serializes user model instances with specific field constraints
    - `UserDetailsView` - Handles authenticated user data retrieval and partial updates

## Important workflows
1. User authentication validation via IsAuthenticated permission
2. User data serialization/deserialization for API responses and updates
3. GET requests retrieve current user details
4. PATCH requests allow partial updates to user profile information

## Implementation notes
- Uses Django REST framework's RetrieveUpdateAPIView for standard CRUD operations
- Email field is read-only to prevent modification through API
- Supports GET and PATCH HTTP methods only
- Returns empty queryset in get_queryset() for django-rest-swagger compatibility
