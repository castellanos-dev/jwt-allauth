## Location
`password_reset.models`

## Purpose
Extends TokenUser from SimpleJWT to provide a custom user ID property for password reset tokens, specifically retrieving the user ID from a predefined token claim.

## Dependencies
- **Internal**:
  - `jwt_allauth.constants` - Provides the FOR_USER constant used to access the user ID claim in the token
- **External**:
  - `django` - Used for cached_property decorator
  - `rest_framework_simplejwt` - Provides base TokenUser class for JWT token handling

## Main structure

### Classes

#### `SetPasswordTokenUser`

  - **Responsibility**: Extends TokenUser to provide a custom user ID retrieval method for password reset tokens
  - **Important attributes**:
    - `token`: [Dict, JWT token payload containing user information]
  - **Primary methods**:
    - `id()`: Returns the user ID from the token's FOR_USER claim, cached for performance

## Usage examples
```python
# TokenUser instance with password reset token
token_user = SetPasswordTokenUser(token_payload)
user_id = token_user.id  # Returns user ID from FOR_USER claim
```
