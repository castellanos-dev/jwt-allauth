# Module: bin

## Location
`bin`

## Module purpose
CLI tool for creating Django projects pre-configured with JWT Allauth authentication system

## Module structure
bin/
│
└── jwt_allauth.py # CLI tool for Django project creation with JWT Allauth

## Relationships with other modules

  - **Dependencies**:
    - `argparse` - Command-line argument parsing
    - `subprocess` - Executing external commands (django-admin)
    - `re` - Regular expressions for file content modification
    - `os` - File system operations
  - **Dependents**:
    - None

## Main interfaces

  - **Exported functions**:
    - `main()` - Main entry point for the CLI tool, handles command routing
    - `_modify_settings(settings_path, email_config)` - Modify Django settings.py to include JWT Allauth configuration
    - `_modify_urls(urls_path)` - Modify Django urls.py to include JWT Allauth URL routes

## Important workflows
1. Parse command-line arguments for project creation
2. Execute django-admin startproject command
3. Modify Django settings.py to configure JWT Allauth authentication
4. Modify Django urls.py to include JWT Allauth URL routes
5. Handle email configuration if specified

## Implementation notes
- Uses subprocess to call external django-admin commands
- Employs regex-based file modification to inject JWT Allauth configuration
- Supports optional email configuration for authentication system
