from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.system_admin.models import ExportJob
from apps.users.models import User
from common.exceptions import ConflictError, NotFoundError, ValidationError

from .audit_service import AdminAuditService
from .csv_export_service import AdminCsvExportService
from .excel_export_service import AdminExcelExportService


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
    def build_user_export_response(cls, *, actor, data: dict[str, Any]):
        """Tạo CSV/XLSX response đồng bộ theo cùng filters/fields với user list/export job."""
        payload = cls.normalize_payload(data)
        fields = payload["fields"]
        export_format = payload["format"]
        queryset = cls._apply_filters(User.objects.all(), payload["filters"]).order_by("id")
        rows = (
            {field: cls._stringify(getattr(user, field, "")) for field in fields}
            for user in queryset.iterator()
        )

        AdminAuditService.log_action(
            action="download_user_export",
            actor=actor,
            target_type="users.User",
            metadata={
                "format": export_format,
                "filters": payload["filters"],
                "fields": fields,
            },
        )

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        filename = f"uevent_users_{timestamp}.{export_format}"
        if export_format == ExportJob.ExportFormat.XLSX:
            return AdminExcelExportService.build_response(
                filename=filename,
                headers=fields,
                rows=rows,
                sheet_name="Users",
            )

        return AdminCsvExportService.build_response(
            filename=filename,
            headers=fields,
            rows=rows,
        )

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
            export_bytes, rows_count, file_extension = cls._build_user_export_bytes(job.request_payload)
            checksum = hashlib.sha256(export_bytes).hexdigest()

            job.status = ExportJob.Status.COMPLETED
            job.progress = 100
            job.completed_at = timezone.now()
            job.file_key = f"exports/users/{job.pk}.{file_extension}"
            job.file_size_bytes = len(export_bytes)
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
    def _build_user_export_bytes(cls, payload: dict[str, Any]) -> tuple[bytes, int, str]:
        normalized_payload = cls.normalize_payload(payload)
        fields = normalized_payload["fields"]
        export_format = normalized_payload["format"]
        queryset = cls._apply_filters(User.objects.all(), normalized_payload["filters"])
        queryset = queryset.order_by("id")

        rows_count = 0

        def iter_rows():
            nonlocal rows_count
            for user in queryset.iterator():
                rows_count += 1
                yield {field: cls._stringify(getattr(user, field, "")) for field in fields}

        if export_format == ExportJob.ExportFormat.XLSX:
            export_bytes = AdminExcelExportService.build_bytes(
                headers=fields,
                rows=iter_rows(),
                sheet_name="Users",
            )
            return export_bytes, rows_count, "xlsx"

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(iter_rows())

        return output.getvalue().encode("utf-8"), rows_count, "csv"

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
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(full_name__icontains=search)
                | Q(student_code__icontains=search)
            )

        return queryset

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)
