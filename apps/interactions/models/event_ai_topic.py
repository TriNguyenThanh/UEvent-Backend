from django.db import models

from common.models import BaseModel


class EventAITopic(BaseModel):
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="ai_topics",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    keywords = models.JSONField(default=list, blank=True)
    reference_content = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        db_table = "event_ai_topics"
        ordering = ["title", "created_at"]
        indexes = [
            models.Index(
                fields=["event", "is_enabled"],
                name="event_ai_to_event_i_8c84c3_idx",
            ),
            models.Index(
                fields=["event", "created_at"],
                name="event_ai_to_event_i_7718a7_idx",
            ),
        ]

    def __str__(self):
        return f"{self.event_id}:{self.title}"
