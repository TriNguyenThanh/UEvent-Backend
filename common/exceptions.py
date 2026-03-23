from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.db import IntegrityError


class BaseAPIException(APIException):
    """Base exception class for API errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"

    def __init__(self, detail=None, code=None, status_code=None):
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail

        if code is not None:
            self.code = code
        else:
            self.code = self.default_code

        if status_code is not None:
            self.status_code = status_code


class ValidationError(BaseAPIException):
    """Validation error exception."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error."
    default_code = "validation_error"


class NotFoundError(BaseAPIException):
    """Not found exception."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = "not_found"


class UnauthorizedError(BaseAPIException):
    """Unauthorized exception."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials were not provided."
    default_code = "unauthorized"


class ForbiddenError(BaseAPIException):
    """Forbidden exception."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "forbidden"


class ConflictError(BaseAPIException):
    """Conflict exception (e.g., duplicate resource)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A resource with this value already exists."
    default_code = "conflict"


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF API views.
    Handles both DRF exceptions and Django exceptions.
    """
    from rest_framework.views import exception_handler as drf_exception_handler

    response = drf_exception_handler(exc, context)

    if response is not None:
        return response

    # Handle Http404
    if isinstance(exc, Http404):
        return Response(
            {
                "error": "not_found",
                "message": str(exc) or "Resource not found.",
                "status_code": status.HTTP_404_NOT_FOUND,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Handle Django ValidationError
    if isinstance(exc, DjangoValidationError):
        error_detail = exc.message if hasattr(exc, "message") else str(exc)
        return Response(
            {
                "error": "validation_error",
                "message": error_detail,
                "status_code": status.HTTP_400_BAD_REQUEST,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Handle IntegrityError
    if isinstance(exc, IntegrityError):
        return Response(
            {
                "error": "conflict",
                "message": "A resource with this value already exists.",
                "status_code": status.HTTP_409_CONFLICT,
            },
            status=status.HTTP_409_CONFLICT,
        )

    # Handle generic exceptions
    return Response(
        {
            "error": "internal_error",
            "message": "An unexpected error occurred.",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
