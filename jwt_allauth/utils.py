from importlib import import_module

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.conf import settings

from django_user_agents.utils import get_user_agent as get_user_agent_django
from six import string_types

from jwt_allauth.constants import TEMPLATE_PATHS
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
        request.user_agent = get_user_agent_django(request)
        request.ip = get_client_ip(request)
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
