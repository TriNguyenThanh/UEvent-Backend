from django.db import models
from django.utils import timezone

from common.models import BaseModel


class EventQuestion(BaseModel):
    class ModerationStatus(models.TextChoices):
        VISIBLE = "visible", "Visible"
        HIDDEN = "hidden", "Hidden"
        FLAGGED = "flagged", "Flagged"

    event = models.ForeignKey(
        "events.Event", on_delete=models.CASCADE, related_name="questions"
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    question_text = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    answer_text = models.TextField(blank=True, null=True)
    answered_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="answered_questions",
    )
    moderation_status = models.CharField(
        max_length=20,
        choices=ModerationStatus.choices,
        default=ModerationStatus.VISIBLE,
    )
    asked_at = models.DateTimeField(default=timezone.now)
    answered_at = models.DateTimeField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "event_questions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "moderation_status", "asked_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"Q:{self.event.pk}:{self.pk}"
