from django.test import SimpleTestCase
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.core.exceptions import custom_exception_handler


class CustomExceptionHandlerTests(SimpleTestCase):
    def test_not_found(self):
        response = custom_exception_handler(NotFound(), {})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "not_found")
        self.assertIsNone(response.data["error"]["details"])

    def test_permission_denied(self):
        response = custom_exception_handler(PermissionDenied(), {})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "permission_denied")

    def test_authentication_failed(self):
        response = custom_exception_handler(AuthenticationFailed(), {})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "authentication_failed")

    def test_field_validation_error(self):
        exc = ValidationError({"email": ["This field is required."]})
        response = custom_exception_handler(exc, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertEqual(
            response.data["error"]["details"], {"email": ["This field is required."]}
        )

    def test_non_field_validation_error(self):
        exc = ValidationError("Something went wrong.")
        response = custom_exception_handler(exc, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["message"], "Something went wrong.")
        self.assertIsNone(response.data["error"]["details"])

    def test_unhandled_exception_passthrough(self):
        self.assertIsNone(custom_exception_handler(Exception("boom"), {}))
