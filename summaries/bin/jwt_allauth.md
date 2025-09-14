## Location
`bin.jwt_allauth`

## Purpose
CLI tool for creating Django projects pre-configured with JWT Allauth authentication system

## Dependencies
- **Internal**:
  - None
- **External**:
  - `argparse` - Command-line argument parsing
  - `subprocess` - Executing external commands (django-admin)
  - `re` - Regular expressions for file content modification
  - `os` - File system operations

## Main structure

### Functions
#### `main()`

  - **Purpose**: Main entry point for the CLI tool, handles command routing
  - **Parameters**:
    - None (uses sys.argv)
  - **Returns**: Exit code (0 for success, 1 for error)

#### `_modify_settings(settings_path, email_config)`

  - **Purpose**: Modify Django settings.py to include JWT Allauth configuration
  - **Parameters**:
    - `settings_path`: str - Path to settings.py file
    - `email_config`: bool - Whether to enable email configuration
  - **Returns**: None (modifies file in place)

#### `_modify_urls(urls_path)`

  - **Purpose**: Modify Django urls.py to include JWT Allauth URL routes
  - **Parameters**:
    - `urls_path`: str - Path to urls.py file
  - **Returns**: None (modifies file in place)

### Global variables/constants

  - None

## Usage examples
```python
# Create a new project with JWT Allauth
jwt-allauth startproject myproject --email True

# Create project in specific directory
jwt-allauth startproject myproject /path/to/project --template custom_template
```
