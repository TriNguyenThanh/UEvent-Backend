from django.db import models
from common.models import BaseModel


class CheckinLog(BaseModel):
    class CheckinResult(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    ticket = models.ForeignKey("registrations.Ticket", on_delete=models.CASCADE, related_name="checkin_logs")
    scanned_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="checkin_logs"
    )
    scanned_at = models.DateTimeField(auto_now_add=True)
    result = models.CharField(max_length=20, choices=CheckinResult.choices)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "checkin_logs"
        ordering = ["-scanned_at", "-created_at"]
        indexes = [
            models.Index(fields=["ticket", "scanned_at"]),
            models.Index(fields=["result", "scanned_at"]),
        ]

    def __str__(self):
        return f"{self.ticket} - {self.result}"

