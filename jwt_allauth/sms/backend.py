import sys
from abc import ABC, abstractmethod

from jwt_allauth import app_settings
from jwt_allauth._importing import import_callable


class BaseSMSBackend(ABC):
    def __init__(self, **kwargs):
        self.options = kwargs

    @abstractmethod
    def send_sms(self, phone_number: str, message: str, **kwargs):
        """
        Send an SMS message to the specified phone number.

        Args:
            phone_number (str): The recipient's phone number (E.164 format recommended).
            message (str): The message content.
            **kwargs: Additional arguments for the specific backend.

        Returns:
            bool: True if sent successfully, False otherwise.
        """


class ConsoleSMSBackend(BaseSMSBackend):
    def send_sms(self, phone_number: str, message: str, **kwargs):
        """
        Write the SMS to the stream (default: stdout).
        """
        stream = kwargs.get('stream', sys.stdout)
        stream.write('SMS to {}:\n{}\n'.format(phone_number, message))
        stream.write('-' * 79)
        stream.write('\n')
        return True


def get_sms_backend():
    backend_class = import_callable(app_settings.SMS_BACKEND)
    opts = app_settings.SMS_OPTS or {}
    return backend_class(**opts)
