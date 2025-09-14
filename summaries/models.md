## Location
`jwt_allauth.models`

## Purpose
Defines custom User model (JAUser) and UserManager for Django authentication with role-based access control.

## Dependencies
- **Internal**:
  - `roles.py` - Provides STAFF_CODE and SUPER_USER_CODE constants for role assignments
- **External**:
  - `django.contrib.auth.models` - AbstractUser, Group, Permission base classes
  - `django.db.models` - Model fields and constraints

## Main structure

### Classes

#### `UserManager`

  - **Responsibility**: Custom user creation with automatic role assignment based on staff/superuser status
  - **Primary methods**:
    - `create_superuser(username, email=None, password=None, **extra_fields)`: Creates superuser with STAFF_CODE role, validates role constraint
    - `create_user(username, email=None, password=None, **extra_fields)`: Creates user with automatic role assignment (STAFF_CODE for staff, SUPER_USER_CODE for superusers)

#### `JAUser`

  - **Responsibility**: Extended Django user model with role-based authorization system
  - **Important attributes**:
    - `role`: PositiveSmallIntegerField - Non-null role identifier (default: 0)
    - `groups`: ManyToManyField to Group - Custom related name "custom_users"
    - `user_permissions`: ManyToManyField to Permission - Custom related name "custom_users"
  - **Invariants**:
    - Staff users must have role=STAFF_CODE
    - Superusers must have role=SUPER_USER_CODE
    - Enforced via database constraints

### Global variables/constants

  - None (constants imported from roles.py)

## Usage examples
```python
# Create staff user
user = JAUser.objects.create_user('staff_user', is_staff=True)
# user.role == STAFF_CODE

# Create superuser
superuser = JAUser.objects.create_superuser('admin', 'admin@example.com', 'password')
# superuser.role == STAFF_CODE, is_staff=True, is_superuser=True
```
