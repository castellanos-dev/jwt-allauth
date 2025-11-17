from allauth.account import app_settings as allauth_app_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context as allauth_ctx
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from jwt_allauth.constants import EMAIL_CONFIRMATION
from jwt_allauth.tokens.serializers import GenericTokenModelSerializer
from jwt_allauth.utils import get_template_path


class JWTAllAuthAdapter(DefaultAccountAdapter):
    """
    Custom account adapter extending allauth's DefaultAccountAdapter with JWT-specific email handling.

    Provides enhanced email confirmation functionality with template path customization
    and JWT-related email content handling.

    Key Features:

        - Email normalization (trimming and lowercasing)
        - Customizable template paths for verification emails
        - Dual template support (HTML/text) with fallback handling
        - Integration with JWT verification workflows
    """
    def clean_email(self, email):
        """
        Normalize email addresses by trimming whitespace and converting to lowercase.

        Args:
            email (str): Raw email input

        Returns:
            str: Normalized email address
        """
        email = super().clean_email(email)
        email = email.strip().lower()
        return email

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Generate and send email confirmation message with context customization.

        Context Includes:

            - User object
            - Verification code or URL (based on EMAIL_VERIFICATION_BY_CODE_ENABLED)
            - Site-specific information

        Args:
            request (HttpRequest): Current request object
            emailconfirmation (EmailConfirmation): Email confirmation instance
            signup (bool): Flag indicating if this is a signup confirmation

        Returns:
            str: Confirmation key used in the email
        """
        confirmation_key = emailconfirmation.key

        user = emailconfirmation.email_address.user
        ctx = {
            "user": user,
        }
        if allauth_app_settings.EMAIL_VERIFICATION_BY_CODE_ENABLED:
            ctx.update({"code": confirmation_key})
        else:
            ctx.update(
                {
                    "key": confirmation_key,
                    "activate_url": self.get_email_confirmation_url(
                        request, emailconfirmation
                    ),
                }
            )
        if signup:
            # Decide which templates to use based on whether the user was invited
            # via admin-managed registration (no usable password yet) or signed
            # up directly (regular self-registration flow).
            is_admin_managed = (
                getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False)
                and not user.has_usable_password()
            )

            if is_admin_managed:
                # Admin-managed invitation email: focuses on confirming email and
                # guiding the user to set their password after verification.
                email_template = "email/admin_invite/email_admin_invite"
                template_path = get_template_path(
                    'ADMIN_EMAIL_VERIFICATION',
                    "email/admin_invite/email_message.html",
                )
                subject_path = get_template_path(
                    'ADMIN_EMAIL_VERIFICATION_SUBJECT',
                    "email/admin_invite/email_subject.txt",
                )
            else:
                # Default self-registration verification email.
                email_template = "email/signup/email_signup"
                template_path = get_template_path(
                    'EMAIL_VERIFICATION',
                    "email/signup/email_message.html",
                )
                subject_path = get_template_path(
                    'EMAIL_VERIFICATION_SUBJECT',
                    "email/signup/email_subject.txt",
                )
        else:
            email_template = "account/email/email_confirmation"
            template_path = None
            subject_path = None
        self.send_mail(
            email_template,
            emailconfirmation.email_address.email,
            ctx,
            subject_path=subject_path,
            template_path=template_path
        )

        # Persist the confirmation key as a generic token so that the verify view
        # can enforce single-use semantics.
        if getattr(settings, 'JWT_ALLAUTH_ADMIN_MANAGED_REGISTRATION', False):
            token_serializer = GenericTokenModelSerializer(
                data={
                    "token": confirmation_key,
                    "user": emailconfirmation.email_address.user.id,
                    "purpose": EMAIL_CONFIRMATION,
                }
            )
            token_serializer.is_valid(raise_exception=True)
            token_serializer.save()

        return confirmation_key

    def send_mail(self, template_prefix, email, context, subject_path=None, template_path=None):
        """
        Construct and send email using template configuration.

        Enhances Context With:

            - Current site information
            - Recipient email address

        Args:
            template_prefix (str): Base path for template lookup
            email (str|list): Recipient email address(es)
            context (dict): Template context variables
            subject_path (str, optional): Custom path for subject template
            template_path (str, optional): Custom path for body template
        """
        ctx = {
            "email": email,
            "current_site": get_current_site(allauth_ctx.request),
        }
        ctx.update(context)
        msg = self.render_mail(template_prefix, email, ctx, subject_path=subject_path, template_path=template_path)
        msg.send()

    def render_mail(self, template_prefix, email, context, headers=None, subject_path=None, template_path=None):
        """
        Render email message with support for multiple template formats and custom paths.

        Behavior:

            - Generates multipart emails when both HTML and text templates exist
            - Uses custom template paths when provided
            - Automatically formats email subject
            - Supports HTML email content as primary when specified

        Args:
            template_prefix (str): Base template path prefix
            email (str|list): Recipient email address(es)
            context (dict): Template context variables
            headers (dict, optional): Custom email headers
            subject_path (str, optional): Override path for subject template
            template_path (str, optional): Override path for body template

        Returns:
            EmailMessage: Configured email message object

        Raises:
            TemplateDoesNotExist: If no valid template can be found
        """
        to = [email] if isinstance(email, str) else email
        if subject_path is None:
            subject_path = "{0}_subject.txt".format(template_prefix)
        subject = render_to_string(subject_path, context)
        # remove superfluous line breaks
        subject = " ".join(subject.splitlines()).strip()
        subject = self.format_email_subject(subject)

        from_email = self.get_from_email()

        if template_path is None:
            bodies = {}
            html_ext = allauth_app_settings.TEMPLATE_EXTENSION
            for ext in [html_ext, "txt"]:
                try:
                    template_name = "{0}_message.{1}".format(template_prefix, ext)
                    bodies[ext] = render_to_string(
                        template_name,
                        context,
                        allauth_ctx.request,
                    ).strip()
                except TemplateDoesNotExist:
                    if ext == "txt" and not bodies:
                        # We need at least one body
                        raise
        else:
            html_ext = 'html'
            bodies = {
                html_ext: render_to_string(
                    template_path,
                    context,
                    allauth_ctx.request,
                ).strip()
            }
        if "txt" in bodies:
            msg = EmailMultiAlternatives(
                subject, bodies["txt"], from_email, to, headers=headers
            )
            if html_ext in bodies:
                msg.attach_alternative(bodies[html_ext], "text/html")
        else:
            msg = EmailMessage(
                subject, bodies[html_ext], from_email, to, headers=headers
            )
            msg.content_subtype = "html"  # Main content is now text/html
        return msg
