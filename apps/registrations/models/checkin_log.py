from django.db import models
from django.utils import timezone
from common.models import BaseModel


class CheckinLog(BaseModel):
    class CheckinResult(models.TextChoices):
        SUCCESS = "success", "Success"
        INVALID_FORMAT = "invalid_format", "Invalid format"
        INVALID_TICKET = "invalid_ticket", "Invalid ticket"
        ALREADY_CHECKED_IN = "already_checked_in", "Already checked in"
        EVENT_UNAVAILABLE = "event_unavailable", "Event unavailable"

    event = models.ForeignKey("events.Event", on_delete=models.RESTRICT, related_name="checkin_logs")
    ticket = models.ForeignKey("registrations.Ticket", on_delete=models.SET_NULL, null=True, blank=True, related_name="checkin_logs")
    scanner_user = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="checkin_scans"
    )
    checked_in_at = models.DateTimeField(default=timezone.now)
    result = models.CharField(max_length=20, choices=CheckinResult.choices)
    note = models.TextField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "checkin_logs"
        ordering = ["-checked_in_at", "-created_at"]
        indexes = [
            models.Index(fields=["ticket", "checked_in_at"]),
            models.Index(fields=["event", "checked_in_at"]),
        ]

    def __str__(self):
        return f"{self.ticket} - {self.result}"

