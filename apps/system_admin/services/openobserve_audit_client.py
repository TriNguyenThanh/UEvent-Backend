from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
from typing import Any
from urllib import error, parse, request

from django.conf import settings

from common.exceptions import ValidationError
from common.response_codes import ResponseCode


class OpenObserveAuditClientError(Exception):
    """Lỗi vận hành khi truy vấn OpenObserve audit logs."""


@dataclass(frozen=True)
class OpenObserveAuditQuery:
    """Input truy vấn audit log đã được validate."""

    filters: dict[str, Any]
    size: int = 50
    date_from: datetime | None = None
    date_to: datetime | None = None
    from_: int = 0


class OpenObserveAuditClient:
    """Client tối thiểu để query audit logs từ OpenObserve với allowlist filter."""

    DEFAULT_TIMEOUT_SECONDS = 5
    DEFAULT_ORGANIZATION = "default"
    DEFAULT_STREAM = "uevent_audit"
    DEFAULT_TIME_RANGE = timedelta(hours=24)
    ALLOWED_FILTERS = {
        "action_type",
        "actor_id",
        "target_type",
        "target_id",
        "system_module",
        "trace_id",
        "level",
        "status",
    }

    def __init__(
        self,
        *,
        base_url: str | None = None,
        organization: str | None = None,
        stream: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or getattr(settings, "OPENOBSERVE_URL", "http://localhost:5080")).rstrip("/")
        self.organization = organization or getattr(
            settings, "OPENOBSERVE_ORGANIZATION", self.DEFAULT_ORGANIZATION
        )
        self.stream = stream or getattr(settings, "OPENOBSERVE_AUDIT_STREAM", self.DEFAULT_STREAM)
        self.timeout = timeout or getattr(settings, "OPENOBSERVE_TIMEOUT_SECONDS", self.DEFAULT_TIMEOUT_SECONDS)
        self.username = getattr(settings, "OPENOBSERVE_USERNAME", "")
        self.password = getattr(settings, "OPENOBSERVE_PASSWORD", "")

    def search(self, query: OpenObserveAuditQuery) -> dict[str, Any]:
        self._validate_filters(query.filters)
        raw_hits = self._request(self._build_body(query, count=False)).get("hits", [])
        raw_count = self._request(self._build_body(query, count=True))
        total = self._extract_total(raw_count)

        return {
            "hits": {
                "total": {"value": total},
                "hits": [self._map_row(row) for row in raw_hits if isinstance(row, dict)],
            }
        }

    def _request(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/{parse.quote(self.organization)}/_search"
        payload = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"

        req = request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise OpenObserveAuditClientError("Không thể truy vấn OpenObserve audit logs.") from exc
        except json.JSONDecodeError as exc:
            raise OpenObserveAuditClientError("OpenObserve trả về dữ liệu không hợp lệ.") from exc

    @classmethod
    def _validate_filters(cls, filters: dict[str, Any]) -> None:
        invalid_filters = sorted(set(filters) - cls.ALLOWED_FILTERS)
        if invalid_filters:
            raise ValidationError(
                detail=f"Filter audit không được hỗ trợ: {', '.join(invalid_filters)}",
                code=ResponseCode.INVALID_AUDIT_FILTER,
            )

    def _build_body(self, query: OpenObserveAuditQuery, *, count: bool) -> dict[str, Any]:
        return {
            "query": {
                "sql": self._build_sql(query, count=count),
                "start_time": self._to_epoch_microseconds(query.date_from or self._default_date_from(query)),
                "end_time": self._to_epoch_microseconds(query.date_to or datetime.now(datetime_timezone.utc)),
                "from": 0 if count else query.from_,
                "size": 1 if count else query.size,
            },
            "search_type": "ui",
            "timeout": self.timeout,
        }

    def _build_sql(self, query: OpenObserveAuditQuery, *, count: bool) -> str:
        select_clause = "COUNT(*) AS total" if count else "*"
        sql = f"SELECT {select_clause} FROM {self._quote_identifier(self.stream)}"
        conditions = self._build_conditions(query.filters)
        if conditions:
            sql = f"{sql} WHERE {' AND '.join(conditions)}"
        if not count:
            sql = f"{sql} ORDER BY _timestamp DESC"
        return sql

    @classmethod
    def _build_conditions(cls, filters: dict[str, Any]) -> list[str]:
        return [
            f"{cls._quote_identifier(key)} = {cls._sql_literal(value)}"
            for key, value in filters.items()
            if value not in (None, "")
        ]

    @staticmethod
    def _quote_identifier(value: str) -> str:
        return f'"{value.replace(chr(34), chr(34) + chr(34))}"'

    @staticmethod
    def _sql_literal(value: Any) -> str:
        return f"'{str(value).replace(chr(39), chr(39) + chr(39))}'"

    @classmethod
    def _default_date_from(cls, query: OpenObserveAuditQuery) -> datetime:
        date_to = query.date_to or datetime.now(datetime_timezone.utc)
        return date_to - cls.DEFAULT_TIME_RANGE

    @staticmethod
    def _to_epoch_microseconds(value: datetime) -> int:
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime_timezone.utc)
        return int(value.timestamp() * 1_000_000)

    @staticmethod
    def _extract_total(payload: dict[str, Any]) -> int:
        hits = payload.get("hits") or []
        if not hits or not isinstance(hits[0], dict):
            return 0

        row = hits[0]
        for key in ("total", "count", "count(*)", "COUNT(*)"):
            if key in row:
                return int(row.get(key) or 0)
        return 0

    @staticmethod
    def _map_row(row: dict[str, Any]) -> dict[str, Any]:
        row_id = row.get("_id") or row.get("id") or row.get("trace_id") or row.get("_timestamp")
        return {
            "_id": str(row_id or ""),
            "_source": row,
        }
