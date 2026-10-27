from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _error_code(exc: exceptions.APIException) -> str:
    codes = exc.get_codes()
    if isinstance(codes, dict):
        return "validation_error"
    if isinstance(codes, list):
        return codes[0] if codes else "error"
    return codes


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, DjangoValidationError):
        # A service (e.g. apps.accounts.services.register_student, via
        # django.contrib.auth.password_validation.validate_password) raising
        # Django's ValidationError - rather than DRF's - would otherwise fall
        # straight through drf_exception_handler (which only recognizes
        # DRF's APIException/Http404/PermissionDenied) as an unhandled 500.
        exc = exceptions.ValidationError(exc.messages)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        message = str(data["detail"])
        details = None
    elif isinstance(data, list):
        message = str(data[0]) if data else "Invalid request."
        details = data if len(data) > 1 else None
    else:
        message = "Validation failed."
        details = data

    response.data = {
        "error": {
            "code": _error_code(exc),
            "message": message,
            "details": details,
        }
    }
    return response
