from django.conf import settings
from django.db import models
from django.db.models import Q

from common.models import BaseModel


class OrganizerRequest(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organizer_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reason = models.TextField()
    proof_file_key = models.CharField(max_length=500)
    proof_file_name = models.CharField(max_length=255)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_organizer_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        db_table = "organizer_requests"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="pending", deleted_at__isnull=True),
                name="uq_organizer_requests_user_pending",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="organizer_r_status_c39d1d_idx",
            ),
            models.Index(
                fields=["user", "status"],
                name="organizer_r_user_id_0c2068_idx",
            ),
            models.Index(
                fields=["reviewed_by", "reviewed_at"],
                name="organizer_r_reviewe_b3c428_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.status}"
