## Location
`jwt_allauth.permissions`

## Purpose
Custom role-based permission classes for Django REST Framework using JWT claims, providing granular access control with automatic staff/superuser privileges.

## Dependencies
- **Internal**:
  - `roles.py` - For STAFF_CODE and SUPER_USER_CODE constants defining privileged role identifiers
- **External**:
  - `rest_framework` - BasePermission class for DRF permission system integration

## Main structure

### Classes

#### `BasePermission`

  - **Responsibility**: Base class for role-based permissions that automatically grants access to staff and superusers in addition to specified roles
  - **Important attributes**:
    - `accepted_roles`: list - Required list of role codes that are allowed access (must be set in subclasses)
  - **Primary methods**:
    - `_check_role_permission(request, include_staff=True)`: Internal method to validate JWT role claims against accepted roles
    - `has_permission(request, view)`: DRF permission check that includes staff/superuser roles by default

#### `BasePermissionStaffExcluded`

  - **Responsibility**: Specialized permission class that excludes automatic staff/superuser access, requiring exact role matches
  - **Important attributes**:
    - `accepted_roles`: list - Required list of role codes that are allowed access (must be set in subclasses)
  - **Primary methods**:
    - `has_permission(request, view)`: DRF permission check that excludes staff/superuser roles

### Global variables/constants

  - None

## Usage examples
```python
# Subclass for specific role requirements
class AdminPermission(BasePermission):
    accepted_roles = ['admin', 'moderator']

# Usage in DRF view
class AdminView(APIView):
    permission_classes = [AdminPermission]
```
