from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.app_settings.models import AppSetting
from common.exceptions import ValidationError

from .audit_service import AdminAuditService


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    group: str
    label: str
    description: str
    value_type: str
    default: Any
    editable: bool = True


class AdminSettingsService:
    GROUPS = [
        # {
        #     "id": "appearance",
        #     "label": "Giao diện",
        #     "description": "Thiết lập trải nghiệm hiển thị trong trang quản trị.",
        # },
        # {
        #     "id": "audit",
        #     "label": "Kiểm toán",
        #     "description": "Thiết lập cảnh báo và quy tắc theo dõi nhật ký quản trị.",
        # },
        # {
        #     "id": "security",
        #     "label": "Bảo mật",
        #     "description": "Thiết lập vận hành an toàn cho cổng quản trị.",
        # },
        # {
        #     "id": "notifications",
        #     "label": "Thông báo",
        #     "description": "Thiết lập gửi thông báo và lịch gửi tự động.",
        # },
        {
            "id": "registration",
            "label": "Đăng ký sự kiện",
            "description": "Thiết lập mặc định cho luồng đăng ký sự kiện.",
        },
    ]

    DEFINITIONS = {
        item.key: item
        for item in [
            SettingDefinition(
                key="appearance.dark_mode",
                group="appearance",
                label="Chế độ tối",
                description="Đồng bộ chế độ tối theo thiết lập hệ thống quản trị.",
                value_type="boolean",
                default=True,
            ),
            SettingDefinition(
                key="audit.alerts_enabled",
                group="audit",
                label="Cảnh báo kiểm toán",
                description="Thông báo khi xuất hiện sự kiện nhật ký quan trọng.",
                value_type="boolean",
                default=True,
            ),
            SettingDefinition(
                key="audit.export_requires_date_range",
                group="audit",
                label="Bắt buộc khoảng ngày khi xuất nhật ký",
                description="Giới hạn export audit để tránh truy vấn quá rộng.",
                value_type="boolean",
                default=True,
                editable=False,
            ),
            SettingDefinition(
                key="security.require_admin_mfa",
                group="security",
                label="Yêu cầu xác thực hai lớp",
                description="Bật yêu cầu MFA cho tài khoản quản trị khi provider hỗ trợ.",
                value_type="boolean",
                default=False,
            ),
            SettingDefinition(
                key="notifications.scheduler_enabled",
                group="notifications",
                label="Bật bộ gửi thông báo đã lên lịch",
                description="Cho phép worker gửi các thông báo đã đến thời điểm lên lịch.",
                value_type="boolean",
                default=True,
            ),
            SettingDefinition(
                key="registration.default_cancellation_hours",
                group="registration",
                label="Giờ hủy đăng ký mặc định",
                description="Số giờ tối thiểu trước sự kiện cho phép người dùng tự hủy đăng ký.",
                value_type="integer",
                default=2,
            ),
        ]
    }

    @classmethod
    def list_settings(cls, *, group: str | None = None) -> dict:
        rows = {
            setting.key: setting
            for setting in AppSetting.objects.filter(key__in=cls.DEFINITIONS.keys()).select_related("updated_by")
        }
        settings = []

        for definition in cls.DEFINITIONS.values():
            if group and definition.group != group:
                continue

            row = rows.get(definition.key)
            settings.append(cls._serialize_setting(definition, row))

        return {"groups": cls.GROUPS, "settings": settings}

    @classmethod
    @transaction.atomic
    def update_settings(cls, *, actor, settings: list[dict], reason: str = "") -> dict:
        updated_keys: list[str] = []

        for item in settings:
            definition = cls.DEFINITIONS.get(item["key"])
            if definition is None:
                raise ValidationError(f"Thiết lập không được hỗ trợ: {item['key']}")

            if not definition.editable:
                raise ValidationError(f"Không được phép chỉnh sửa thiết lập hệ thống: {item['key']}")

            value = cls._coerce_value(definition, item["value"])
            AppSetting.objects.update_or_create(
                key=definition.key,
                defaults={
                    "value": json.dumps(value, ensure_ascii=False),
                    "description": definition.description,
                    "updated_by": actor,
                },
            )
            updated_keys.append(definition.key)

        if updated_keys:
            AdminAuditService.log_action(
                action="update_settings",
                actor=actor,
                target_type="app_settings.AppSetting",
                target_id=",".join(updated_keys),
                reason=reason,
                metadata={"updated_keys": updated_keys},
            )

        return cls.list_settings()

    @classmethod
    def _serialize_setting(cls, definition: SettingDefinition, row: AppSetting | None) -> dict:
        value = definition.default
        updated_at = None
        updated_by = None

        if row is not None:
            value = cls._parse_stored_value(row.value, definition.default)
            updated_at = row.updated_at
            updated_by = row.updated_by.get_full_name() or row.updated_by.username if row.updated_by else None

        return {
            "key": definition.key,
            "group": definition.group,
            "label": definition.label,
            "description": definition.description,
            "value_type": definition.value_type,
            "value": value,
            "editable": definition.editable,
            "updated_at": updated_at,
            "updated_by": updated_by,
        }

    @staticmethod
    def _parse_stored_value(raw_value: str, default: Any) -> Any:
        try:
            return json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return default

    @staticmethod
    def _coerce_value(definition: SettingDefinition, value: Any) -> Any:
        if definition.value_type == "boolean":
            if not isinstance(value, bool):
                raise ValidationError(f"Giá trị của {definition.key} phải là boolean.")
            return value

        if definition.value_type == "integer":
            if isinstance(value, bool):
                raise ValidationError(f"Giá trị của {definition.key} phải là số nguyên.")
            try:
                next_value = int(value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"Giá trị của {definition.key} phải là số nguyên.") from exc
            if next_value < 0:
                raise ValidationError(f"Giá trị của {definition.key} không được âm.")
            return next_value

        if definition.value_type == "string":
            if not isinstance(value, str):
                raise ValidationError(f"Giá trị của {definition.key} phải là chuỗi.")
            return value

        return value
