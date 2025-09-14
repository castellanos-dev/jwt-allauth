## Location
`jwt_allauth.adapter`

## Purpose
Custom Django AllAuth account adapter providing JWT-specific email handling with enhanced template customization and email confirmation workflows.

## Dependencies
- **Internal**:
  - `jwt_allauth.utils` - For template path resolution utilities
- **External**:
  - `allauth.account` - For account settings and base adapter functionality
  - `allauth.core` - For request context handling
  - `django.contrib.sites` - For current site information
  - `django.core.mail` - For email message construction
  - `django.template` - For template rendering and exception handling

## Main structure

### Classes

#### `JWTAllAuthAdapter`

  - **Responsibility**: Extends AllAuth's DefaultAccountAdapter to provide JWT-aware email confirmation with custom template paths and email normalization
  - **Important attributes**:
    - Inherits all attributes from DefaultAccountAdapter
  - **Primary methods**:
    - `clean_email(email)`: Normalizes email by trimming whitespace and converting to lowercase
    - `send_confirmation_mail(request, emailconfirmation, signup)`: Generates and sends email confirmation with JWT-specific context
    - `send_mail(template_prefix, email, context, subject_path, template_path)`: Constructs and sends email using custom template configuration
    - `render_mail(template_prefix, email, context, headers, subject_path, template_path)`: Renders email message with support for multiple formats and custom paths

### Functions
*No standalone functions in this file*

### Global variables/constants
*No global variables or constants defined*

## Usage examples
```python
# Typical adapter usage in Django settings
ACCOUNT_ADAPTER = 'jwt_allauth.adapter.JWTAllAuthAdapter'

# Email confirmation flow automatically uses custom adapter
adapter = JWTAllAuthAdapter()
key = adapter.send_confirmation_mail(request, email_confirmation, signup=True)
```

## Test Criteria
- Verify email normalization handles various input formats
- Test email confirmation with both code and URL verification methods
- Validate custom template path resolution for signup vs regular confirmation
- Ensure multipart email generation (HTML/text) works correctly
- Test template fallback behavior when templates are missing
- Verify site context is properly included in email templates
- Test email subject formatting and line break handling
- Validate exception handling for missing templates
