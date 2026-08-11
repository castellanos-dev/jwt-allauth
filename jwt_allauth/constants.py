PASS_RESET = 'PASS_RESET'
PASS_RESET_ACCESS = 'PASS_RESET_ACCESS'
TEMPLATE_PATHS = 'JWT_ALLAUTH_TEMPLATES'

EMAIL_VERIFIED_REDIRECT = 'EMAIL_VERIFIED_REDIRECT'
PASSWORD_RESET_REDIRECT = 'PASSWORD_RESET_REDIRECT'

PASS_RESET_COOKIE = 'password_reset_access_token'

FOR_USER = 'for_user'
ONE_TIME_PERMISSION = 'one_time_permission'

REFRESH_TOKEN_COOKIE = 'refresh_token'

# Session
# Claim holding the timestamp at which the session started. Unlike ``iat``, it is preserved
# across refresh token rotations, so it is available as an anchor whenever an installation
# opts into an absolute session lifetime through JWT_ALLAUTH_SESSION_LIFETIME.
SESSION_IAT_CLAIM = 'session_iat'

# Admin-managed registration & email confirmation flow
PASS_SET = 'PASS_SET'
PASS_SET_ACCESS = 'PASS_SET_ACCESS'
PASSWORD_SET_REDIRECT = 'PASSWORD_SET_REDIRECT'
SET_PASSWORD_COOKIE = 'set_password_access_token'
EMAIL_CONFIRMATION = 'EMAIL_CONFIRMATION'
EMAIL_VERIFICATION_FAILED_TEMPLATE = 'EMAIL_VERIFICATION_FAILED_TEMPLATE'

# MFA
MFA_SALT = 'jwt_allauth_mfa'
MFA_TOKEN_MAX_AGE_SECONDS = 300

# MFA brute force limits
# Failed verifications tolerated on a single login challenge before it is invalidated.
MFA_CHALLENGE_MAX_ATTEMPTS = 5
# Failed verifications tolerated per user, across every challenge, within the lockout
# window. Without it an attacker holding the password could simply request a fresh
# challenge after every invalidation and keep guessing codes for free.
MFA_USER_MAX_ATTEMPTS = 10
# Sliding window used both to count the failed attempts of a user and to decide how
# long a locked out user has to wait before the MFA step accepts codes again.
MFA_LOCKOUT_SECONDS = 900

# MFA TOTP modes
MFA_TOTP_DISABLED = 'disabled'
MFA_TOTP_OPTIONAL = 'optional'
MFA_TOTP_REQUIRED = 'required'

# MFA token purposes
MFA_PURPOSE_SETUP_CHALLENGE = 'mfa_setup_challenge'
MFA_PURPOSE_LOGIN_CHALLENGE = 'mfa_login_challenge'
MFA_PURPOSE_SETUP_SECRET = 'mfa_setup_secret'
MFA_PURPOSE_LOGIN_ATTEMPT = 'mfa_login_attempt'
