## Location
`registration.urls`

## Purpose
Defines URL patterns for user registration and email verification endpoints in a Django REST framework application using JWT and allauth integration.

## Dependencies
- **Internal**:
  - `jwt_allauth.registration.views` - Provides RegisterView for user registration
  - `jwt_allauth.registration.email_verification.views` - Provides VerifyEmailView for email confirmation
  - `jwt_allauth.utils` - Provides get_template_path utility function
  - `jwt_allauth.constants` - Provides EMAIL_VERIFIED_REDIRECT constant
- **External**:
  - `django.conf.settings` - Access application configuration
  - `django.urls.path` - URL routing
  - `django.views.generic.TemplateView` - Simple template rendering views

## Main structure

### Classes
#### `RegisterView` (imported)
  - **Responsibility**: Handles user registration requests, typically processing POST requests with user credentials
  - **Primary methods**:
    - `as_view()`: Returns view function for URL routing

#### `VerifyEmailView` (imported)
  - **Responsibility**: Handles email verification requests using verification keys
  - **Primary methods**:
    - `as_view()`: Returns view function for URL routing

#### `TemplateView` (imported)
  - **Responsibility**: Renders simple templates for static pages like verification sent confirmation and verified success pages

### Global variables/constants
  - `EMAIL_VERIFIED_REDIRECT`: Configuration setting that determines redirect behavior after email verification
  - `EMAIL_VERIFICATION`: Boolean setting that controls whether email verification features are enabled

## Usage examples
```python
# Registration endpoint
POST /api/auth/registration/

# Email verification endpoint (when enabled)
GET /api/auth/registration/verification/{key}/

# Verification sent confirmation page
GET /api/auth/registration/account_email_verification_sent/

# Email verified success page
GET /api/auth/registration/verified/
```

## Test criteria
- Test registration endpoint accepts valid user data and returns appropriate responses
- Verify email verification flow works correctly when EMAIL_VERIFICATION is enabled
- Test that verification endpoints return proper HTTP status codes
- Confirm template views render expected templates
- Validate URL patterns resolve to correct views with proper names
- Test conditional URL patterns based on settings configuration
