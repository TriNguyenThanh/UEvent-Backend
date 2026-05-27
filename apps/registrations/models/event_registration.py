from django.db import models
from common.models import BaseModel


class EventRegistration(BaseModel):
    class RegistrationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        REGISTERED = "registered", "Registered"
        WAITLISTED = "waitlisted", "Waitlisted"
        CANCEL_PENDING = "cancel_pending", "Cancel pending"
        CANCELLED = "cancelled", "Cancelled"
        REJECTED = "rejected", "Rejected"
        CHECKED_IN = "checked_in", "Checked in"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_registrations")
    status = models.CharField(max_length=24, choices=RegistrationStatus.choices, default=RegistrationStatus.PENDING)
    form_answers_jsonb = models.JSONField(default=dict, blank=True)
    answers_locked = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=500, blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "event_registrations"
        ordering = ["-registered_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="uq_event_registrations_event_user")
        ]
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["event", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.event}"


