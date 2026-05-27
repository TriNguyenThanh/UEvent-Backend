from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response

from common.response_codes import ResponseCode


RESPONSE_CODE_MESSAGES: dict[ResponseCode, str] = {
    ResponseCode.SUCCESS: "Success.",
    ResponseCode.CREATED: "Created successfully.",
    ResponseCode.UPDATED: "Updated successfully.",
    ResponseCode.DELETED: "Deleted successfully.",
    ResponseCode.ACCEPTED: "Request accepted.",
    ResponseCode.EXPORT_READY: "Export file is ready.",
    ResponseCode.API_ERROR: "API error.",
    ResponseCode.VALIDATION_ERROR: "Validation error.",
    ResponseCode.NOT_FOUND: "Resource not found.",
    ResponseCode.METHOD_NOT_ALLOWED: "Method not allowed.",
    ResponseCode.CONFLICT: "Resource conflict.",
    ResponseCode.RATE_LIMITED: "Too many requests.",
    ResponseCode.INTERNAL_ERROR: "An unexpected error occurred.",
    ResponseCode.SERVICE_UNAVAILABLE: "Service unavailable.",
    ResponseCode.UNAUTHORIZED: "Authentication credentials were not provided.",
    ResponseCode.FORBIDDEN: "You do not have permission to perform this action.",
    ResponseCode.INVALID_CREDENTIALS: "Invalid credentials.",
    ResponseCode.ACCOUNT_DISABLED: "Account is disabled.",
    ResponseCode.INSUFFICIENT_PERMISSIONS: "Insufficient permissions.",
    ResponseCode.INVALID_AUDIT_FILTER: "Invalid audit filter.",
    ResponseCode.AUDIT_SEARCH_UNAVAILABLE: "Audit search is unavailable.",
    ResponseCode.EXPORT_FAILED: "Export failed.",
}


def normalize_response_code(code: ResponseCode | str) -> str:
    """Đưa response code về chuỗi ổn định cho client."""
    if isinstance(code, ResponseCode):
        return code.value
    return str(code)


def get_default_message(code: ResponseCode | str, success: bool) -> str:
    """Lấy message mặc định theo mã response."""
    if isinstance(code, ResponseCode):
        return RESPONSE_CODE_MESSAGES.get(code, "Success." if success else "API error.")
    return "Success." if success else "API error."


def build_api_response(
    *,
    success: bool,
    code: ResponseCode | str,
    message: str | None = None,
    data: Any = None,
    errors: Any = None,
    meta: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build envelope chuẩn dùng chung cho success và error."""
    response_meta = dict(meta or {})
    if request_id is not None:
        response_meta["request_id"] = request_id

    return {
        "success": success,
        "code": normalize_response_code(code),
        "message": message or get_default_message(code, success),
        "data": data if success else None,
        "errors": None if success else errors,
        "meta": response_meta,
    }


def api_response(
    *,
    success: bool,
    code: ResponseCode | str,
    message: str | None = None,
    data: Any = None,
    errors: Any = None,
    meta: dict[str, Any] | None = None,
    request_id: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Trả DRF Response theo envelope chuẩn."""
    return Response(
        build_api_response(
            success=success,
            code=code,
            message=message,
            data=data,
            errors=errors,
            meta=meta,
            request_id=request_id,
        ),
        status=status_code,
    )


def success_response(
    *,
    data: Any = None,
    code: ResponseCode = ResponseCode.SUCCESS,
    message: str | None = None,
    meta: dict[str, Any] | None = None,
    request_id: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """Trả response thành công theo envelope chuẩn."""
    return api_response(
        success=True,
        code=code,
        message=message,
        data=data,
        errors=None,
        meta=meta,
        request_id=request_id,
        status_code=status_code,
    )


def created_response(
    *,
    data: Any = None,
    message: str | None = None,
    meta: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> Response:
    """Trả response tạo mới theo envelope chuẩn."""
    return success_response(
        data=data,
        code=ResponseCode.CREATED,
        message=message,
        meta=meta,
        request_id=request_id,
        status_code=status.HTTP_201_CREATED,
    )


def deleted_response(
    *,
    message: str | None = None,
    meta: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> Response:
    """Trả response xóa/vô hiệu hóa theo envelope chuẩn."""
    return success_response(
        data=None,
        code=ResponseCode.DELETED,
        message=message,
        meta=meta,
        request_id=request_id,
        status_code=status.HTTP_200_OK,
    )


def error_response(
    *,
    code: ResponseCode | str,
    message: str | None = None,
    errors: Any = None,
    meta: dict[str, Any] | None = None,
    request_id: str | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """Trả response lỗi theo envelope chuẩn."""
    return api_response(
        success=False,
        code=code,
        message=message,
        data=None,
        errors=errors,
        meta=meta,
        request_id=request_id,
        status_code=status_code,
    )
