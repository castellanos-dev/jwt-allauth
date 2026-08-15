import unittest

from django.test import SimpleTestCase

from jwt_allauth.constants import PASS_RESET_COOKIE
from jwt_allauth.schema import SCHEMA_ANNOTATIONS_AVAILABLE


def _generate():
    from drf_spectacular.generators import SchemaGenerator

    return SchemaGenerator().get_schema(request=None, public=True)


@unittest.skipUnless(SCHEMA_ANNOTATIONS_AVAILABLE, 'drf-spectacular is not installed')
class OpenAPISchemaTests(SimpleTestCase):
    """
    The generated schema has to describe what the endpoints answer and how they are
    authorized, neither of which follows from the serializer they validate with.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = _generate()

    def operation(self, path, method='post'):
        return self.schema['paths'][path][method]

    def properties(self, operation, code):
        ref = operation['responses'][code]['content']['application/json']['schema']['$ref']
        return self.schema['components']['schemas'][ref.rsplit('/', 1)[-1]]['properties']

    def test_registration_documents_the_token_it_answers_with(self):
        """
        The 201 used to be derived from the request serializer, so it announced ``email``
        and ``first_name`` where the response actually carries the session.
        """
        properties = self.properties(self.operation('/jwt-allauth/registration/'), '201')
        self.assertIn('access', properties)
        self.assertIn('refresh', properties)
        self.assertNotIn('password1', properties)

    def test_capability_endpoint_documents_its_cookie_and_csrf_header(self):
        """
        These endpoints take no bearer token, so nothing in a serializer-derived schema
        told an integrator what to send.
        """
        parameters = {
            (p['name'], p['in']) for p in self.operation('/jwt-allauth/password/reset/set-new/')['parameters']
        }
        self.assertIn((PASS_RESET_COOKIE, 'cookie'), parameters)
        self.assertIn(('X-CSRFToken', 'header'), parameters)

    def test_throttling_mixin_does_not_describe_the_endpoints(self):
        """
        The mixin comes first on the MRO of every view that uses it, so its docstring
        became the description of the login, registration, refresh and MFA endpoints.
        """
        paths = (
            '/jwt-allauth/login/',
            '/jwt-allauth/registration/',
            '/jwt-allauth/refresh/',
            '/jwt-allauth/social/{provider}/token/',
            '/jwt-allauth/social/{provider}/code/',
            '/jwt-allauth/social/{provider}/connect/token/',
        )
        for path in paths:
            description = self.operation(path).get('description', '')
            self.assertNotIn('throttle', description.lower(), path)
            self.assertTrue(description.strip(), path)

    def test_social_login_documents_the_session_and_the_mfa_challenge(self):
        """
        The social logins answer either with a session or with an MFA challenge, and a
        frontend has to know both shapes are the same 200.
        """
        properties = self.properties(self.operation('/jwt-allauth/social/{provider}/token/'), '200')
        self.assertIn('access', properties)
        self.assertIn('mfa_required', properties)
        self.assertIn('challenge_id', properties)
        self.assertNotIn('id_token', properties)

    def test_connect_documents_the_connection_it_answers_with(self):
        """
        Undecorated, spectacular derived the response from the request serializer — a
        200 whose every field is write-only, i.e. an empty body, for an endpoint that
        answers 201 with a SocialAccount.
        """
        operation = self.operation('/jwt-allauth/social/{provider}/connect/token/')
        properties = self.properties(operation, '201')
        self.assertIn('provider', properties)
        self.assertIn('uid', properties)
        self.assertNotIn('id_token', properties)
