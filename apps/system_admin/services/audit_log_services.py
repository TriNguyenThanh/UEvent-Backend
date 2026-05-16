from __future__ import annotations

from uuid import UUID
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from common.exceptions import BaseAPIException
from common.response_codes import ResponseCode

from .audit_service import AdminAuditService
from .csv_export_service import AdminCsvExportService
from .excel_export_service import AdminExcelExportService
from .opensearch_audit_client import OpenSearchAuditClient, OpenSearchAuditClientError, OpenSearchAuditQuery


class AuditSearchUnavailableError(BaseAPIException):
    status_code = 503
    default_detail = "Không thể truy vấn nhật ký kiểm toán."
    default_code = ResponseCode.AUDIT_SEARCH_UNAVAILABLE


class AdminAuditLogService:
    EXPORT_HEADERS = [
        "timestamp",
        "actor_id",
        "actor_name",
        "action_type",
        "target_type",
        "target_id",
        "status",
        "level",
        "system_module",
        "trace_id",
        "reason",
    ]

    @classmethod
    def search_logs(cls, *, filters: dict, client: OpenSearchAuditClient | None = None) -> dict:
        page = max(1, int(filters.get("page") or 1))
        page_size = max(1, min(100, int(filters.get("page_size") or 20)))
        query = OpenSearchAuditQuery(
            filters=cls._build_term_filters(filters),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            size=page_size,
            from_=(page - 1) * page_size,
        )

        raw = cls._execute_search(query, client=client)
        logs = cls._enrich_actor_profiles(
            [cls._map_hit(hit) for hit in raw.get("hits", {}).get("hits", [])]
        )
        total = cls._get_total(raw)
        total_pages = max(1, (total + page_size - 1) // page_size)

        return {
            "logs": logs,
            "pagination": {
                "count": total,
                "next": None,
                "previous": None,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        }

    @classmethod
    def export_logs(cls, *, actor, filters: dict):
        result = cls.search_logs(
            filters={
                **filters,
                "page": 1,
                "page_size": 100,
            }
        )
        rows = [cls._to_export_row(log) for log in result["logs"]]
        export_format = filters.get("export_format") or "csv"

        AdminAuditService.log_action(
            action="export_audit_logs",
            actor=actor,
            target_type="system_admin.audit_log",
            reason="Xuất nhật ký kiểm toán từ trang quản trị.",
            metadata={
                "date_from": filters["date_from"].isoformat(),
                "date_to": filters["date_to"].isoformat(),
                "rows_count": len(rows),
                "export_format": export_format,
            },
        )

        filename = f"audit_logs_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
        if export_format == "xlsx":
            return AdminExcelExportService.build_response(
                filename=filename,
                headers=cls.EXPORT_HEADERS,
                rows=rows,
                sheet_name="Audit Logs",
            )

        return AdminCsvExportService.build_response(
            filename=filename,
            headers=cls.EXPORT_HEADERS,
            rows=rows,
        )

    @classmethod
    def get_summary(cls, *, client: OpenSearchAuditClient | None = None) -> dict:
        now = timezone.now()
        query = OpenSearchAuditQuery(
            filters={},
            date_from=now - timezone.timedelta(hours=24),
            date_to=now,
            size=25,
        )
        try:
            raw = cls._execute_search(query, client=client)
        except AuditSearchUnavailableError:
            return {
                "total_events": 0,
                "failed_events": 0,
                "high_risk_events": 0,
                "last_event_at": None,
                "status": "unavailable",
            }

        logs = cls._enrich_actor_profiles(
            [cls._map_hit(hit) for hit in raw.get("hits", {}).get("hits", [])]
        )
        failed = [log for log in logs if log["status"] == "failed"]
        high_risk = [
            log for log in logs
            if log["action_type"] in {"ban_user", "soft_delete_user", "delete_event", "export_audit_logs"}
        ]
        last_event_at = logs[0]["timestamp"] if logs else None

        return {
            "total_events": cls._get_total(raw),
            "failed_events": len(failed),
            "high_risk_events": len(high_risk),
            "last_event_at": last_event_at,
            "status": "available",
        }

    @staticmethod
    def _build_term_filters(filters: dict) -> dict:
        allowed_keys = [
            "actor_id",
            "action_type",
            "target_type",
            "target_id",
            "status",
            "level",
        ]
        return {
            key: filters.get(key)
            for key in allowed_keys
            if filters.get(key) not in (None, "")
        }

    @staticmethod
    def _execute_search(query: OpenSearchAuditQuery, *, client: OpenSearchAuditClient | None = None) -> dict:
        try:
            return (client or OpenSearchAuditClient()).search(query)
        except OpenSearchAuditClientError as exc:
            raise AuditSearchUnavailableError(detail=str(exc), code=ResponseCode.AUDIT_SEARCH_UNAVAILABLE) from exc

    @staticmethod
    def _get_total(raw: dict) -> int:
        total = raw.get("hits", {}).get("total", 0)
        if isinstance(total, dict):
            return int(total.get("value") or 0)
        return int(total or 0)

    @classmethod
    def _map_hit(cls, hit: dict) -> dict:
        source = hit.get("_source", {})
        timestamp = cls._parse_timestamp(source)
        level = str(source.get("level") or source.get("levelname") or "INFO").upper()
        action_type = str(source.get("action_type") or "")
        actor_id = str(source.get("actor_id") or "")
        actor_username = str(source.get("actor_username") or source.get("username") or "")
        actor_email = str(source.get("actor_email") or source.get("email") or "")
        actor_name = str(
            source.get("actor_name")
            or source.get("full_name")
            or actor_username
            or actor_email
            or "Hệ thống"
        )

        return {
            "id": str(hit.get("_id") or source.get("id") or source.get("trace_id") or timestamp.isoformat()),
            "timestamp": timestamp,
            "actor": {
                "id": actor_id,
                "name": actor_name,
                "username": actor_username,
                "email": actor_email,
            },
            "action_type": action_type,
            "target": {
                "type": str(source.get("target_type") or ""),
                "id": str(source.get("target_id") or ""),
            },
            "reason": str(source.get("reason") or ""),
            "status": str(source.get("status") or ("failed" if level in {"ERROR", "CRITICAL"} else "success")),
            "level": level,
            "system_module": str(source.get("system_module") or ""),
            "trace_id": str(source.get("trace_id") or source.get("span_id") or ""),
            "metadata": source.get("metadata") or {},
        }

    @staticmethod
    def _parse_timestamp(source: dict) -> timezone.datetime:
        value = source.get("event_time") or source.get("timestamp") or source.get("@timestamp")
        if isinstance(value, str):
            parsed = timezone.datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
        return timezone.now()

    @classmethod
    def _enrich_actor_profiles(cls, logs: list[dict]) -> list[dict]:
        actor_ids = {
            actor_id
            for log in logs
            if (actor_id := cls._normalize_actor_id(log.get("actor", {}).get("id")))
        }
        if not actor_ids:
            for log in logs:
                actor = log.get("actor", {})
                actor["name"] = cls._resolve_unknown_actor_name(actor)
            return logs

        user_model = get_user_model()
        users_by_id = {
            str(user.id): user
            for user in user_model.objects.filter(id__in=actor_ids).only("id", "username", "email", "full_name")
        }

        for log in logs:
            actor = log.get("actor", {})
            actor_id = cls._normalize_actor_id(actor.get("id"))
            user = users_by_id.get(actor_id or "")
            if not user:
                actor["name"] = cls._resolve_unknown_actor_name(actor)
                continue

            actor["id"] = str(user.id)
            actor["name"] = cls._format_actor_name(user)
            actor["username"] = user.username or ""
            actor["email"] = user.email or ""

        return logs

    @staticmethod
    def _normalize_actor_id(value: Any) -> str | None:
        actor_id = str(value or "").strip()
        if not actor_id:
            return None
        try:
            return str(UUID(actor_id))
        except ValueError:
            return None

    @staticmethod
    def _format_actor_name(user) -> str:
        return user.full_name or user.username or user.email or "Người dùng không xác định"

    @staticmethod
    def _resolve_unknown_actor_name(actor: dict) -> str:
        current_name = str(actor.get("name") or "").strip()
        actor_id = str(actor.get("id") or "").strip()
        if current_name and current_name != actor_id and not (actor_id and current_name == "Hệ thống"):
            return current_name
        return str(actor.get("username") or actor.get("email") or "").strip() or "Người dùng không xác định"

    @staticmethod
    def _to_export_row(log: dict) -> dict:
        return {
            "timestamp": log["timestamp"].isoformat(),
            "actor_id": log["actor"]["id"],
            "actor_name": log["actor"]["name"],
            "action_type": log["action_type"],
            "target_type": log["target"]["type"],
            "target_id": log["target"]["id"],
            "status": log["status"],
            "level": log["level"],
            "system_module": log["system_module"],
            "trace_id": log["trace_id"],
            "reason": log["reason"],
        }
