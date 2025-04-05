from typing import Union

from django.utils.functional import cached_property
from rest_framework_simplejwt.models import TokenUser

from jwt_allauth.constants import FOR_USER


class SetPasswordTokenUser(TokenUser):
    @cached_property
    def id(self) -> Union[int, str]:
        return self.token[FOR_USER]
