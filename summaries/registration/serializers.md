## Location
`registration.serializers`

## Purpose
Provides Django REST Framework serializers for user registration, handling validation, cleaning, and user creation with email verification support.

## Dependencies
- **Internal**:
  - None
- **External**:
  - `allauth.account` - User account management and email handling
  - `django` - Web framework core functionality
  - `rest_framework` - API serialization framework
  - `re` - Regular expression pattern matching

## Main structure

### Classes

#### `RegisterSerializer`

  - **Responsibility**: Validates and processes user registration data, creates user accounts with proper email verification flow
  - **Important attributes**:
    - `_has_phone_field`: Boolean flag indicating phone field presence (currently False)
  - **Primary methods**:
    - `validate_username(username)`: Cleans and validates username format
    - `validate_email(email)`: Validates email uniqueness and cleans existing unverified entries
    - `validate_password1(password)`: Validates password strength
    - `validate_first_name(first_name)`: Validates and formats first name (letters and spaces only, capitalized)
    - `validate_last_name(last_name)`: Validates and formats last name (letters and spaces only, capitalized)
    - `validate(data)`: Compares password fields for match
    - `get_cleaned_data()`: Returns dictionary of validated registration data
    - `save(request)`: Atomic transaction that creates user, sets up email, and handles verification

## Usage examples
```python
serializer = RegisterSerializer(data={
    'email': 'user@example.com',
    'password1': 'securepass123',
    'password2': 'securepass123',
    'first_name': 'john',
    'last_name': 'doe'
})
if serializer.is_valid():
    user = serializer.save(request)
```
