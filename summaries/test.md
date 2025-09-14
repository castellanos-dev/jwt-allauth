## Location
`jwt_allauth.test`

## Purpose
Provides testing utilities for JWT-authenticated Django applications, including a custom test client and base test case with pre-configured authentication tokens.

## Dependencies
- **Internal**:
  - `jwt_allauth.tokens.app_settings` - Used to generate JWT refresh tokens for test users
- **External**:
  - `django` - Web framework for test client and test case base
  - `allauth.account` - Used for user field management and email address verification
  - `jwt` - Token generation and handling (implied through RefreshToken usage)

## Main structure

### Classes

#### `JAClient`

  - **Responsibility**: Extends Django test client to automatically handle JWT authentication headers for various HTTP methods
  - **Important attributes**:
    - `ACCESS`: str - Regular user JWT access token
    - `STAFF_ACCESS`: str - Staff user JWT access token
    - `content_type`: str - Default content type for requests (application/json)
  - **Primary methods**:
    - `update_kwargs(access_token=None, default_auth=False, staff_auth=False, **kwargs)`: Prepares request kwargs with appropriate Authorization header
    - Standard HTTP methods with auth variants: post/auth_post/staff_post, get/auth_get/staff_get, patch/auth_patch/staff_patch, put/auth_put/staff_put, delete/auth_delete/staff_delete

#### `JATestCase`

  - **Responsibility**: Base test case that sets up authenticated test environment with regular and staff users
  - **Important attributes**:
    - `USER`: User - Regular test user instance
    - `STAFF_USER`: User - Staff test user instance
    - `ACCESS`: str - Regular user access token
    - `STAFF_ACCESS`: str - Staff user access token
    - Pre-defined user credentials (EMAIL, PASS, FIRST_NAME, LAST_NAME, etc.)
  - **Primary methods**:
    - `setUp()`: Creates test users, verifies emails, and generates JWT tokens
    - `ja_client`: Property that returns pre-configured JAClient instance
    - `authenticate(user)`: Updates access token for a specific user

## Usage examples
```python
# In a test class inheriting from JATestCase
def test_authenticated_endpoint(self):
    response = self.ja_client.auth_get('/api/protected/')
    self.assertEqual(response.status_code, 200)

def test_staff_only_endpoint(self):
    response = self.ja_client.staff_get('/api/admin/')
    self.assertEqual(response.status_code, 200)
```
