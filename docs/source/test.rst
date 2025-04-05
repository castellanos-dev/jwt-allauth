Test utils
----------

JWT allauth provides a custom :class:`~jwt_allauth.test.JATestCase` that simplifies the authentication process in your django tests.

    * Default user loaded in the database. The user info is defined in the ``EMAIL``, ``PASS``, ``FIRST_NAME`` and
      ``LAST_NAME`` attributes. The user model object is available at the ``USER`` attribute.

    * Staff user loaded in the database. The user info is defined in the ``STAFF_EMAIL``, ``STAFF_PASS``,
      ``STAFF_FIRST_NAME`` and ``STAFF_LAST_NAME`` attributes. The user model object is available at the ``STAFF_USER``
      attribute.

    * :class:`~jwt_allauth.test.JAClient` client accessible via ``JATestCase.ja_client`` property.

        * JSON content type automatically set.

        * Bearer access token configurable via the ``access_token`` parameter in the ``get``, ``post``, ``patch`` and
          ``put`` methods.

        * ``JATestCase.USER`` automatic authentication through the ``auth_get``, ``auth_post``, ``auth_patch`` and
          ``auth_put`` methods.

        * ``JATestCase.STAFF_USER`` automatic authentication through the ``staff_get``, ``staff_post``,
          ``staff_patch`` and ``staff_put`` methods.

Usage example
"""""""""""""

.. code-block:: python

    from jwt_allauth.test import JATestCase
    from django.urls import reverse

    class ExampleTest(JATestCase):

        def test_patch_user_details(self):
            payload = {"first_name": "other name"}
            self.assertNotEqual(self.USER.first_name, payload["first_name"])
            resp = self.ja_client.auth_patch(reverse("rest_user_details"), data=payload)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["first_name"], payload["first_name"])
