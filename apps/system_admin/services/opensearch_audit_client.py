from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib import error, request

from django.conf import settings

from common.exceptions import ValidationError
from common.response_codes import ResponseCode


class OpenSearchAuditClientError(Exception):
    """Lỗi vận hành khi truy vấn OpenSearch audit logs."""


@dataclass(frozen=True)
class OpenSearchAuditQuery:
    """Input truy vấn audit log đã được validate."""

    filters: dict[str, Any]
    size: int = 50
    date_from: datetime | None = None
    date_to: datetime | None = None
    from_: int = 0


class OpenSearchAuditClient:
    """Client tối thiểu để query audit logs từ OpenSearch với allowlist filter."""

    DEFAULT_TIMEOUT_SECONDS = 5
    DEFAULT_INDEX = "uevent-audit-*"
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

    def __init__(self, *, base_url: str | None = None, index: str | None = None, timeout: int | None = None):
        self.base_url = (base_url or getattr(settings, "OPENSEARCH_URL", "http://localhost:9200")).rstrip("/")
        self.index = index or getattr(settings, "OPENSEARCH_AUDIT_INDEX", self.DEFAULT_INDEX)
        self.timeout = timeout or getattr(settings, "OPENSEARCH_TIMEOUT_SECONDS", self.DEFAULT_TIMEOUT_SECONDS)
        self.username = getattr(settings, "OPENSEARCH_USERNAME", "")
        self.password = getattr(settings, "OPENSEARCH_PASSWORD", "")

    def search(self, query: OpenSearchAuditQuery) -> dict[str, Any]:
        self._validate_filters(query.filters)
        body = self._build_body(query)
        url = f"{self.base_url}/{self.index}/_search"
        payload = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"

        req = request.Request(
            url,
            data=payload,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise OpenSearchAuditClientError("Không thể truy vấn OpenSearch audit logs.") from exc
        except json.JSONDecodeError as exc:
            raise OpenSearchAuditClientError("OpenSearch trả về dữ liệu không hợp lệ.") from exc

    @classmethod
    def _validate_filters(cls, filters: dict[str, Any]) -> None:
        invalid_filters = sorted(set(filters) - cls.ALLOWED_FILTERS)
        if invalid_filters:
            raise ValidationError(
                detail=f"Filter audit không được hỗ trợ: {', '.join(invalid_filters)}",
                code=ResponseCode.INVALID_AUDIT_FILTER,
            )

    @staticmethod
    def _build_body(query: OpenSearchAuditQuery) -> dict[str, Any]:
        filters = [
            {"term": {key: value}}
            for key, value in query.filters.items()
            if value not in (None, "")
        ]
        return {
            "from": query.from_,
            "size": query.size,
            "sort": [{"event_time": {"order": "desc", "unmapped_type": "date"}}],
            "query": {
                "bool": {
                    "filter": [
                        *filters,
                        *OpenSearchAuditClient._build_date_filters(query),
                    ]
                }
            }
            if filters or query.date_from or query.date_to
            else {"match_all": {}},
        }

    @staticmethod
    def _build_date_filters(query: OpenSearchAuditQuery) -> list[dict[str, Any]]:
        range_filter: dict[str, str] = {}
        if query.date_from:
            range_filter["gte"] = query.date_from.isoformat()
        if query.date_to:
            range_filter["lte"] = query.date_to.isoformat()
        return [{"range": {"event_time": range_filter}}] if range_filter else []
