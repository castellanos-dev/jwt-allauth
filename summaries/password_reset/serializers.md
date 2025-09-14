## Location
`password_reset.serializers`

## Purpose
Handles password reset requests and password setting operations via serializers for Django REST Framework.

## Dependencies
- **Internal**:
  - `jwt_allauth.constants` - Provides constant `PASS_RESET` for token generation purpose
  - `jwt_allauth.password_change.serializers` - Base class for `SetPasswordSerializer`
  - `jwt_allauth.tokens.tokens` - Provides `GenericToken` for generating password reset tokens
  - `jwt_allauth.utils` - Provides `get_template_path` for email template resolution
- **External**:
  - `allauth.account.adapter` - Version unknown, used for email validation
  - `allauth.account.models` - Version unknown, used to check email verification status
  - `django.conf.settings` - Version unknown, accesses `DEFAULT_FROM_EMAIL` setting
  - `django.contrib.auth.forms` - Version unknown, uses `PasswordResetForm` for validation
  - `django.contrib.sites.requests` - Version unknown, provides `RequestSite` for domain override
  - `rest_framework.serializers` - Version unknown, base serializer classes and fields

## Main structure

### Classes

#### `PasswordResetSerializer`

  - **Responsibility**: Validates email and sends password reset email if email is verified
  - **Important attributes**:
    - `email`: EmailField, the email address for password reset
    - `password_reset_form_class`: Class, defaults to `PasswordResetForm`
    - `reset_form`: Instance, created during validation
  - **Primary methods**:
    - `get_email_options()`: Returns empty dict by default, can be overridden to customize email options
    - `validate_email(value)`: Validates email using allauth adapter and password reset form
    - `save()`: Sends password reset email if email is verified, using configured options

#### `SetPasswordSerializer`

  - **Responsibility**: Handles password setting without requiring old password validation
  - **Important attributes**:
    - `old_password`: None, explicitly disabled
    - `old_password_field_enabled`: False, disables old password requirement
    - `logout_on_password_change`: False, prevents automatic logout
  - **Primary methods**:
    - `__init__(*args, **kwargs)`: Removes old_password field and configures password change behavior
    - `validate_old_password(value)`: No-op method to satisfy parent class interface

## Usage examples
```python
# Password reset request
serializer = PasswordResetSerializer(data={'email': 'user@example.com'}, context={'request': request})
if serializer.is_valid():
    serializer.save()

# Set new password
serializer = SetPasswordSerializer(data={'new_password1': 'newpass123', 'new_password2': 'newpass123'})
if serializer.is_valid():
    serializer.save()
```
