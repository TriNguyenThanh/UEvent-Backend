from django.db import models
from common.models import BaseModel


class ModerationLog(BaseModel):
    class Action(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        HIDE = "hide", "Hide"
        FLAG = "flag", "Flag"
        REOPEN = "reopen", "Reopen"
        ESCALATE = "escalate", "Escalate"

    event = models.ForeignKey(
        "events.Event", on_delete=models.SET_NULL, null=True, blank=True, related_name="moderation_logs"
    )
    actor = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="moderation_actions"
    )
    target_type = models.CharField(max_length=50)
    target_id = models.UUIDField()
    action = models.CharField(max_length=20, choices=Action.choices)
    reason = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        db_table = "moderation_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action}:{self.target_type}:{self.target_id}"


