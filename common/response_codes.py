from enum import Enum


class ResponseCode(str, Enum):
    """Mã response dùng chung cho toàn backend."""

    SUCCESS = "success"
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACCEPTED = "accepted"
    EXPORT_READY = "export_ready"

    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"

    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_DISABLED = "account_disabled"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"

    INVALID_AUDIT_FILTER = "invalid_audit_filter"
    AUDIT_SEARCH_UNAVAILABLE = "audit_search_unavailable"
    EXPORT_FAILED = "export_failed"

    def __str__(self) -> str:
        return self.value
