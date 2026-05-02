import logging
import traceback

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from opentelemetry import trace
from rest_framework import status
from rest_framework.exceptions import APIException, ErrorDetail
from rest_framework.response import Response


class BaseAPIException(APIException):
    """Base exception class for API errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = "error"

    def __init__(self, detail=None, code=None, status_code=None):
        super().__init__(detail=detail or self.default_detail, code=code or self.default_code)

        if code is not None:
            self.code = code

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


def get_request_id(context=None) -> str | None:
    """Lấy trace/request correlation ID cho response lỗi."""
    request = (context or {}).get("request")
    if request is not None:
        request_id = getattr(request, "request_id", None) or request.headers.get("X-Request-ID")
        if request_id:
            return str(request_id)

    span = trace.get_current_span()
    span_context = span.get_span_context() if span is not None else None
    if span_context and span_context.is_valid:
        return format(span_context.trace_id, "032x")

    return None


def build_error_response(*, code: str, message: str, details=None, request_id: str | None, status_code: int) -> dict:
    """Chuẩn hóa error response cho API production."""
    return {
        "code": code,
        "message": message,
        "details": details,
        "request_id": request_id,
    }


def _stringify_error_detail(detail):
    if isinstance(detail, ErrorDetail):
        return str(detail)
    if isinstance(detail, list):
        return [_stringify_error_detail(item) for item in detail]
    if isinstance(detail, dict):
        return {key: _stringify_error_detail(value) for key, value in detail.items()}
    return detail


def _extract_exception_code(exc, fallback: str) -> str:
    code = getattr(exc, "code", None)
    if code:
        return str(code)

    detail = getattr(exc, "detail", None)
    if isinstance(detail, ErrorDetail):
        return str(detail.code)

    if isinstance(detail, dict):
        return fallback

    return fallback


def _format_drf_error(exc, response, request_id: str | None) -> Response:
    detail = _stringify_error_detail(response.data)
    code = _extract_exception_code(exc, "api_error")

    if isinstance(detail, dict):
        message = detail.get("detail") or detail.get("non_field_errors") or "Validation error."
        if isinstance(message, list):
            message = " ".join(str(item) for item in message)
        details = detail
    elif isinstance(detail, list):
        message = " ".join(str(item) for item in detail)
        details = detail
    else:
        message = str(detail)
        details = None

    response.data = build_error_response(
        code=code,
        message=message,
        details=details,
        request_id=request_id,
        status_code=response.status_code,
    )
    return response


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF API views.
    Schema production: {code, message, details, request_id}.
    """
    from rest_framework.views import exception_handler as drf_exception_handler

    request_id = get_request_id(context)
    response = drf_exception_handler(exc, context)

    if response is not None:
        return _format_drf_error(exc, response, request_id)

    if isinstance(exc, Http404):
        return Response(
            build_error_response(
                code="not_found",
                message=str(exc) or "Resource not found.",
                details=None,
                request_id=request_id,
                status_code=status.HTTP_404_NOT_FOUND,
            ),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, DjangoValidationError):
        error_detail = exc.message_dict if hasattr(exc, "message_dict") else getattr(exc, "message", str(exc))
        return Response(
            build_error_response(
                code="validation_error",
                message="Validation error.",
                details=error_detail,
                request_id=request_id,
                status_code=status.HTTP_400_BAD_REQUEST,
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            build_error_response(
                code="conflict",
                message="A resource with this value already exists.",
                details=None,
                request_id=request_id,
                status_code=status.HTTP_409_CONFLICT,
            ),
            status=status.HTTP_409_CONFLICT,
        )

    logging.getLogger('django.request').error(
        f"Internal Server Error [{request_id}]: {exc}\n{traceback.format_exc()}"
    )

    return Response(
        build_error_response(
            code="internal_error",
            message="An unexpected error occurred.",
            details=None,
            request_id=request_id,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
