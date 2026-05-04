from django.conf import settings
from django.db import models

from common.models import BaseModel


class ExportJob(BaseModel):
    """Theo dõi job export dữ liệu admin theo contract async."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    class ExportType(models.TextChoices):
        USERS = "users", "Users"

    class ExportFormat(models.TextChoices):
        CSV = "csv", "CSV"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_export_jobs",
    )
    export_type = models.CharField(
        max_length=50,
        choices=ExportType.choices,
        default=ExportType.USERS,
    )
    export_format = models.CharField(
        max_length=20,
        choices=ExportFormat.choices,
        default=ExportFormat.CSV,
    )
    idempotency_key = models.CharField(max_length=255)
    request_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    retry_count = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    file_key = models.CharField(max_length=500, blank=True)
    download_url = models.URLField(blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    rows_count = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        db_table = "admin_export_jobs"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["actor", "idempotency_key"],
                name="uq_admin_export_jobs_actor_idempotency_key",
            ),
        ]
        indexes = [
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["export_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.export_type}:{self.id} ({self.status})"
