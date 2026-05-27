from django.db import models
from django.utils import timezone

from common.models import BaseModel


class RegistrationCancellationRequest(BaseModel):
    class RequestStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    registration = models.ForeignKey(
        "registrations.EventRegistration",
        on_delete=models.CASCADE,
        related_name="cancellation_requests",
    )
    event = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, related_name="cancellation_requests"
    )
    requester_user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancellation_requests",
    )
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING
    )
    requested_at = models.DateTimeField(default=timezone.now)
    reviewed_by_user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_cancellation_requests",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "registration_cancellation_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["registration", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Cancel request {self.registration.id} ({self.status})"
