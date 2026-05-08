import logging
from collections.abc import Mapping
from typing import Any

from django.utils import timezone


audit_logger = logging.getLogger("uevent.audit")


class AdminAuditService:
    """Service ghi audit log chuẩn cho system admin."""

    SENSITIVE_KEYS = {
        "authorization",
        "access",
        "access_token",
        "refresh",
        "refresh_token",
        "token",
        "password",
        "secret",
        "api_key",
    }
    MASK_VALUE = "***REDACTED***"

    @classmethod
    def log_action(
        cls,
        *,
        action: str,
        actor,
        target_type: str,
        target_id: str | None = None,
        reason: str = "",
        metadata: Mapping[str, Any] | None = None,
        system_module: str = "system_admin",
    ) -> None:
        """Ghi audit event, tự động mask field nhạy cảm."""
        audit_logger.info(
            f"Admin action: {action}",
            extra={
                "action_type": action,
                "actor_id": str(getattr(actor, "pk", "")),
                "target_type": target_type,
                "target_id": str(target_id or ""),
                "reason": reason,
                "system_module": system_module,
                "event_time": timezone.now().isoformat(),
                "metadata": cls.mask_sensitive_data(dict(metadata or {})),
            },
        )

    @classmethod
    def mask_sensitive_data(cls, value: Any) -> Any:
        """Mask recursively các field không được phép ghi vào audit log."""
        if isinstance(value, Mapping):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                if key_text.lower() in cls.SENSITIVE_KEYS:
                    sanitized[key_text] = cls.MASK_VALUE
                else:
                    sanitized[key_text] = cls.mask_sensitive_data(item)
            return sanitized

        if isinstance(value, list):
            return [cls.mask_sensitive_data(item) for item in value]

        if isinstance(value, tuple):
            return tuple(cls.mask_sensitive_data(item) for item in value)

        return value
