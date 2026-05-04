from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.system_admin.models import ExportJob
from apps.users.models import User
from common.exceptions import ConflictError, NotFoundError, ValidationError

from .audit_service import AdminAuditService


class AdminUserExportService:
    """Business logic cho async user export job."""

    EXPORT_TTL_HOURS = 24
    DEFAULT_FIELDS = [
        "id",
        "username",
        "email",
        "full_name",
        "student_code",
        "faculty",
        "class_name",
        "account_status",
        "is_active",
        "created_at",
    ]
    ALLOWED_FIELDS = set(DEFAULT_FIELDS) | {
        "phone_number",
        "updated_at",
        "deleted_at",
    }
    ALLOWED_FILTERS = {
        "account_status",
        "faculty",
        "is_active",
        "search",
    }

    @classmethod
    def normalize_payload(cls, data: dict[str, Any]) -> dict[str, Any]:
        filters = data.get("filters") or {}
        fields = data.get("fields") or cls.DEFAULT_FIELDS
        export_format = data.get("format") or ExportJob.ExportFormat.CSV

        return {
            "format": export_format,
            "filters": filters,
            "fields": fields,
        }

    @classmethod
    def create_user_export_job(
        cls,
        *,
        actor,
        idempotency_key: str | None,
        data: dict[str, Any],
    ) -> tuple[ExportJob, bool]:
        """Tạo job export user theo Idempotency-Key; trả job cũ nếu request lặp lại."""
        normalized_key = (idempotency_key or "").strip()
        if not normalized_key:
            raise ValidationError("Idempotency-Key header is required.")

        payload = cls.normalize_payload(data)
        expires_at = timezone.now() + timezone.timedelta(hours=cls.EXPORT_TTL_HOURS)

        with transaction.atomic():
            existing_job = (
                ExportJob.all_objects.select_for_update()
                .filter(actor=actor, idempotency_key=normalized_key, deleted_at__isnull=True)
                .first()
            )
            if existing_job is not None:
                if existing_job.request_payload != payload:
                    raise ConflictError("Idempotency-Key already exists with a different export payload.")
                return existing_job, False

            job = ExportJob.objects.create(
                actor=actor,
                export_type=ExportJob.ExportType.USERS,
                export_format=payload["format"],
                idempotency_key=normalized_key,
                request_payload=payload,
                status=ExportJob.Status.PENDING,
                progress=0,
                expires_at=expires_at,
            )

            AdminAuditService.log_action(
                action="request_user_export",
                actor=actor,
                target_type="system_admin.ExportJob",
                target_id=str(job.pk),
                metadata={
                    "export_type": job.export_type,
                    "format": job.export_format,
                    "filters": payload["filters"],
                    "fields": payload["fields"],
                },
            )

            return job, True

    @staticmethod
    def get_export_job(*, actor, job_id) -> ExportJob:
        queryset = ExportJob.all_objects.filter(deleted_at__isnull=True)
        if not getattr(actor, "is_superuser", False):
            queryset = queryset.filter(actor=actor)

        try:
            return queryset.get(pk=job_id)
        except ExportJob.DoesNotExist as exc:
            raise NotFoundError(f"Export job with ID {job_id} does not exist.") from exc

    @classmethod
    @transaction.atomic
    def process_user_export_job(cls, *, job_id) -> ExportJob:
        """
        Xử lý job export user bằng fallback đồng bộ.

        Khi Celery/storage được cấu hình, worker có thể gọi method này từ queue exports.
        """
        job = ExportJob.all_objects.select_for_update().get(pk=job_id)
        if job.status == ExportJob.Status.COMPLETED:
            return job

        job.status = ExportJob.Status.PROCESSING
        job.progress = 10
        job.started_at = timezone.now()
        job.save(update_fields=["status", "progress", "started_at", "updated_at"])

        try:
            csv_bytes, rows_count = cls._build_user_export_bytes(job.request_payload)
            checksum = hashlib.sha256(csv_bytes).hexdigest()

            job.status = ExportJob.Status.COMPLETED
            job.progress = 100
            job.completed_at = timezone.now()
            job.file_key = f"exports/users/{job.pk}.csv"
            job.file_size_bytes = len(csv_bytes)
            job.checksum_sha256 = checksum
            job.rows_count = rows_count
            job.error_code = ""
            job.error_message = ""
            job.save(
                update_fields=[
                    "status",
                    "progress",
                    "completed_at",
                    "file_key",
                    "file_size_bytes",
                    "checksum_sha256",
                    "rows_count",
                    "error_code",
                    "error_message",
                    "updated_at",
                ]
            )
        except Exception as exc:
            job.status = ExportJob.Status.FAILED
            job.progress = 100
            job.completed_at = timezone.now()
            job.error_code = "export_failed"
            job.error_message = str(exc)
            job.save(
                update_fields=[
                    "status",
                    "progress",
                    "completed_at",
                    "error_code",
                    "error_message",
                    "updated_at",
                ]
            )
            raise

        return job

    @classmethod
    def _build_user_export_bytes(cls, payload: dict[str, Any]) -> tuple[bytes, int]:
        fields = payload.get("fields") or cls.DEFAULT_FIELDS
        queryset = cls._apply_filters(User.objects.all(), payload.get("filters") or {})
        queryset = queryset.order_by("id")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        rows_count = 0
        for user in queryset.iterator():
            writer.writerow({field: cls._stringify(getattr(user, field, "")) for field in fields})
            rows_count += 1

        return output.getvalue().encode("utf-8"), rows_count

    @classmethod
    def _apply_filters(cls, queryset, filters: dict[str, Any]):
        account_status = filters.get("account_status")
        if account_status:
            queryset = queryset.filter(account_status=account_status)

        faculty = filters.get("faculty")
        if faculty:
            queryset = queryset.filter(faculty=faculty)

        if "is_active" in filters:
            queryset = queryset.filter(is_active=filters["is_active"])

        search = filters.get("search")
        if search:
            queryset = queryset.filter(username__icontains=search) | queryset.filter(email__icontains=search)

        return queryset

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)
