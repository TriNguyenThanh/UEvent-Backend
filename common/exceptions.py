import logging
import traceback

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from opentelemetry import trace
from rest_framework import status
from rest_framework.exceptions import APIException, ErrorDetail
from rest_framework.response import Response

from common.response_codes import ResponseCode
from common.responses import build_api_response


class BaseAPIException(APIException):
    """Base exception class for API errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An error occurred."
    default_code = ResponseCode.API_ERROR

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
    default_code = ResponseCode.VALIDATION_ERROR


class NotFoundError(BaseAPIException):
    """Not found exception."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = ResponseCode.NOT_FOUND


class UnauthorizedError(BaseAPIException):
    """Unauthorized exception."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials were not provided."
    default_code = ResponseCode.UNAUTHORIZED


class ForbiddenError(BaseAPIException):
    """Forbidden exception."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = ResponseCode.FORBIDDEN


class ConflictError(BaseAPIException):
    """Conflict exception (e.g., duplicate resource)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A resource with this value already exists."
    default_code = ResponseCode.CONFLICT


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


def build_error_response(*, code: ResponseCode | str, message: str, errors=None, request_id: str | None) -> dict:
    """Chuẩn hóa error response theo envelope chung."""
    return build_api_response(
        success=False,
        code=code,
        message=message,
        data=None,
        errors=errors,
        request_id=request_id,
    )


def _stringify_error_detail(detail):
    if isinstance(detail, ErrorDetail):
        return str(detail)
    if isinstance(detail, list):
        return [_stringify_error_detail(item) for item in detail]
    if isinstance(detail, dict):
        return {key: _stringify_error_detail(value) for key, value in detail.items()}
    return detail


def _extract_exception_code(exc, fallback: ResponseCode) -> ResponseCode | str:
    from rest_framework.exceptions import NotAuthenticated, PermissionDenied

    if isinstance(exc, NotAuthenticated):
        return ResponseCode.UNAUTHORIZED

    if isinstance(exc, PermissionDenied):
        return ResponseCode.FORBIDDEN

    code = getattr(exc, "code", None)
    if code:
        return code

    detail = getattr(exc, "detail", None)
    if isinstance(detail, ErrorDetail):
        return str(detail.code)

    if isinstance(detail, dict):
        return fallback

    return fallback


def _format_drf_error(exc, response, request_id: str | None) -> Response:
    detail = _stringify_error_detail(response.data)
    code = _extract_exception_code(exc, ResponseCode.API_ERROR)

    if isinstance(detail, dict):
        message = detail.get("detail") or detail.get("non_field_errors") or "Validation error."
        if isinstance(message, list):
            message = " ".join(str(item) for item in message)
        errors = detail
    elif isinstance(detail, list):
        message = " ".join(str(item) for item in detail)
        errors = detail
    else:
        message = str(detail)
        errors = None

    response.data = build_error_response(
        code=code,
        message=message,
        errors=errors,
        request_id=request_id,
    )
    return response


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF API views.
    Schema production: {success, code, message, data, errors, meta}.
    """
    from rest_framework.views import exception_handler as drf_exception_handler

    request_id = get_request_id(context)
    response = drf_exception_handler(exc, context)

    if response is not None:
        return _format_drf_error(exc, response, request_id)

    if isinstance(exc, Http404):
        return Response(
            build_error_response(
                code=ResponseCode.NOT_FOUND,
                message=str(exc) or "Resource not found.",
                errors=None,
                request_id=request_id,
            ),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, DjangoValidationError):
        error_detail = exc.message_dict if hasattr(exc, "message_dict") else getattr(exc, "message", str(exc))
        return Response(
            build_error_response(
                code=ResponseCode.VALIDATION_ERROR,
                message="Validation error.",
                errors=error_detail,
                request_id=request_id,
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            build_error_response(
                code=ResponseCode.CONFLICT,
                message="A resource with this value already exists.",
                errors=None,
                request_id=request_id,
            ),
            status=status.HTTP_409_CONFLICT,
        )

    logging.getLogger('django.request').error(
        f"Internal Server Error [{request_id}]: {exc}\n{traceback.format_exc()}"
    )

    return Response(
        build_error_response(
            code=ResponseCode.INTERNAL_ERROR,
            message="An unexpected error occurred.",
            errors=None,
            request_id=request_id,
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
