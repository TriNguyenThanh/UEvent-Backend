from django.db import models
from common.models import BaseModel


class ModerationLog(BaseModel):
    class Action(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        REQUEST_REVISION = "request_revision", "Request revision"
        LOCK = "lock", "Lock"
        DELETE = "delete", "Delete"
        REOPEN = "reopen", "Reopen"
        ESCALATE = "escalate", "Escalate"

    event = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, related_name="moderation_logs"
    )
    admin_user = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_moderation_logs"
    )
    report_type = models.CharField(max_length=50, blank=True, null=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    reason = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        db_table = "event_moderation_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "created_at"]),
            models.Index(fields=["admin_user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action}:{self.event_id}"


