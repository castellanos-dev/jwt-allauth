## Location
`registration.email_verification.serializers`

## Purpose
Defines a serializer for email verification requests, specifically handling the verification key input.

## Dependencies
- **External**:
  - `rest_framework` - Provides serializers for request/response data validation and transformation

## Main structure

### Classes

#### `VerifyEmailSerializer`

  - **Responsibility**: Validates and deserializes email verification requests containing a verification key
  - **Important attributes**:
    - `key`: CharField, required string field for the email verification token
  - **Primary methods**:
    - Inherits standard Serializer methods (validate, save, etc.) from rest_framework

## Usage examples
```python
# Validate email verification request
serializer = VerifyEmailSerializer(data={'key': 'abc123-verification-token'})
if serializer.is_valid():
    verified_key = serializer.validated_data['key']
    # Process verification
```
