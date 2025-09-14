## Location
`roles.py`

## Purpose
Defines role-based access control constants for user privilege levels in the system.

## Dependencies
- **Internal**: None
- **External**: None

## Main structure

### Classes
None

### Functions
None

### Global variables/constants
  - `STAFF_CODE`: 1000 - Privilege code for staff members
  - `SUPER_USER_CODE`: 900 - Privilege code for super users
  - `USER_CODE`: 0 - Privilege code for regular users

## Usage examples
```python
# Check user access level
if user_role_code >= STAFF_CODE:
    grant_admin_access()
```
