from importlib import import_module
from typing import Any, Dict, Optional

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.conf import settings

from django_user_agents.utils import get_user_agent as get_user_agent_django
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken
from six import string_types

from jwt_allauth.constants import TEMPLATE_PATHS, REFRESH_TOKEN_COOKIE
from jwt_allauth.exceptions import NotVerifiedEmail, IncorrectCredentials


def import_callable(path_or_callable):
    """
    Convert a Python path string to a callable object or return the input if already callable.

    Args:
        path_or_callable (str|callable): Either a Python path string (module.attribute)
                                        or an already callable object

    Returns:
        callable: The resolved callable object

    Raises:
        AssertionError: If input is string but not valid Python path
    """
    if hasattr(path_or_callable, '__call__'):
        return path_or_callable
    else:
        assert isinstance(path_or_callable, string_types)
        package, attr = path_or_callable.rsplit('.', 1)
        return getattr(import_module(package), attr)


def get_client_ip(request):
    """
    Extract client IP address from request metadata.

    Priority:

        1. X-Forwarded-For header (first entry if multiple)
        2. REMOTE_ADDR meta value

    Args:
        request (HttpRequest): Django request object

    Returns:
        str: Client IP address or None if not found
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(f):
    """
    Decorator that adds user agent and IP information to the request object.

    Stores:
    - user_agent: Parsed user agent details
    - ip: Client IP address

    Args:
        f (function): View method to decorate

    Returns:
        function: Decorated view method
    """
    def user_agent(self, request, *args, **kwargs):
        if getattr(settings, 'JWT_ALLAUTH_COLLECT_USER_AGENT', False):
            request.user_agent = get_user_agent_django(request)
            request.ip = get_client_ip(request)
        else:
            request.user_agent = None
            request.ip = None
        return f(self, request, *args, **kwargs)

    return user_agent


def user_agent_dict(request):
    """
    Generate a detailed dictionary of user agent information.

    Includes:

        - Browser details (name, version)
        - OS details (name, version)
        - Device information (family, brand, model)
        - Network information (IP address)
        - Device type flags (mobile, tablet, PC, bot)

    Args:
        request (HttpRequest): Django request object

    Returns:
        dict: Structured user agent details. Empty dict if no request.
    """
    if request is None:
        return {}
    if request.user_agent is None:
        return {}
    return {
        'browser': request.user_agent.browser.family,
        'browser_version': request.user_agent.browser.version_string,
        'os': request.user_agent.os.family,
        'os_version': request.user_agent.os.version_string,
        'device': request.user_agent.device.family,
        'device_brand': request.user_agent.device.brand,
        'device_model': request.user_agent.device.model,
        'ip': request.ip,
        'is_mobile': request.user_agent.is_mobile,
        'is_tablet': request.user_agent.is_tablet,
        'is_pc': request.user_agent.is_pc,
        'is_bot': request.user_agent.is_bot,
    }


sensitive_post_parameters_m = method_decorator(
    sensitive_post_parameters(
        'password', 'old_password', 'new_password1', 'new_password2', 'password1', 'password2'
    )
)


def get_template_path(constant, default):
    """
    Get template path from settings using TEMPLATE_PATHS configuration.

    Args:
        constant (str): Key to look up in TEMPLATE_PATHS setting
        default (str): Default path if not found in settings

    Returns:
        str: Configured template path or default value
    """
    templates_path_dict = getattr(settings, TEMPLATE_PATHS, {})
    return getattr(templates_path_dict, constant, default)


def is_email_verified(user, raise_exception=False):
    """
    Check if user has a verified email address.

    Args:
        user (User): User object to check
        raise_exception (bool): Whether to raise NotVerifiedEmail if unverified

    Returns:
        bool: True if verified, False otherwise

    Raises:
        NotVerifiedEmail: If raise_exception=True and email is unverified
    """
    if not EmailAddress.objects.filter(user=user.id, verified=True).exists():
        if raise_exception:
            raise NotVerifiedEmail()
        return False
    return True


def allauth_authenticate(**kwargs):
    """
    Authenticate user using allauth's adapter with enhanced verification.

    Args:
        **kwargs: Authentication credentials (typically username/email + password)

    Returns:
        User: Authenticated user object

    Raises:
        IncorrectCredentials: If authentication fails
        NotVerifiedEmail: If email is not verified
    """
    user = get_adapter().authenticate(**kwargs)
    if user is None:
        raise IncorrectCredentials()
    is_email_verified(user, raise_exception=True)
    return user


def load_user(f):
    """
    Decorator that loads the complete user object from the database for stateless JWT authentication.
    This is necessary because JWT tokens only contain the user ID, and the full user object
    might be needed in the view methods.

    Usage:

    .. code-block:: python

        @load_user
        def my_view_method(self, *args, **kwargs):
            # self.request.user will be the complete user object
            pass
    """
    def wrapper(self, *args, **kwargs):
        try:
            self.request.user = get_user_model().objects.get(id=self.request.user.id)
        except get_user_model().DoesNotExist:
            raise InvalidToken()
        res = f(self, *args, **kwargs)
        return res
    return wrapper


def build_token_response(
    refresh_token: Any,
    access_token: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
    http_status: int = status.HTTP_200_OK,
    cookie_settings: Optional[Dict[str, Any]] = None,
) -> Response:
    """
    Build a standardized token response with optional refresh token as cookie.

    This helper function standardizes the token response format across the application,
    handling both cookie-based and JSON-based refresh token delivery based on settings.

    Args:
        refresh_token: RefreshToken instance or string representation
        access_token: Optional access token string. If not provided, will be extracted from refresh_token
        extra_data: Optional dictionary of additional data to include in response
        http_status: HTTP status code for the response (default: 200 OK)
        cookie_settings: Optional dictionary with custom cookie settings. Keys can include:
                        - 'key': Cookie name (default: REFRESH_TOKEN_COOKIE)
                        - 'httponly': Whether cookie is HTTP only (default: True)
                        - 'secure': Whether cookie requires HTTPS (default: based on DEBUG)
                        - 'samesite': SameSite policy (default: 'Lax')
                        - 'max_age': Cookie max age in seconds (default: None)

    Returns:
        Response: DRF Response object with tokens and optional cookie set

    Example:
        .. code-block:: python

            from jwt_allauth.utils import build_token_response
            from jwt_allauth.tokens.app_settings import RefreshToken

            # Basic usage
            refresh = RefreshToken.for_user(user)
            response = build_token_response(refresh)

            # With custom data
            response = build_token_response(
                refresh,
                extra_data={"detail": "Login successful"},
                http_status=status.HTTP_201_CREATED
            )

            # With custom cookie settings
            response = build_token_response(
                refresh,
                cookie_settings={
                    'max_age': 86400,  # 24 hours
                    'samesite': 'Strict'
                }
            )
    """
    # Extract access token if not provided
    if access_token is None:
        if hasattr(refresh_token, 'access_token'):
            access_token = str(refresh_token.access_token)
        else:
            access_token = str(refresh_token)

    # Build response data
    response_data: Dict[str, Any] = {"access": access_token}

    # Add refresh token to response if not using cookies
    use_cookie = getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_AS_COOKIE", True)
    if not use_cookie:
        response_data["refresh"] = str(refresh_token)

    # Add extra data if provided
    if extra_data:
        response_data.update(extra_data)

    # Create response
    response = Response(response_data, status=http_status)

    # Set cookie if configured
    if use_cookie:
        # Prepare default cookie settings
        default_settings = {
            'key': REFRESH_TOKEN_COOKIE,
            'value': str(refresh_token),
            'httponly': getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_HTTP_ONLY", True),
            'secure': getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SECURE", not settings.DEBUG),
            'samesite': getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_SAME_SITE", "Lax"),
            'max_age': getattr(settings, "JWT_ALLAUTH_REFRESH_TOKEN_COOKIE_MAX_AGE", None),
        }

        # Override with custom settings if provided
        if cookie_settings:
            default_settings.update(cookie_settings)

        response.set_cookie(**default_settings)

    return response
