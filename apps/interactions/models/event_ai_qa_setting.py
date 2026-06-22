from decimal import Decimal

from django.db import models

from common.models import BaseModel


class EventAIQASetting(BaseModel):
    class Mode(models.TextChoices):
        DRAFT = "draft", "Draft"
        AUTO_PUBLISH = "auto_publish", "Auto publish"

    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="ai_qa_setting",
    )
    is_enabled = models.BooleanField(default=False)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.DRAFT)
    organizer_instructions = models.TextField(blank=True)
    min_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=Decimal("0.5"),
    )

    class Meta(BaseModel.Meta):
        db_table = "event_ai_qa_settings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["event", "is_enabled"],
                name="event_ai_qa_event_i_48d1c3_idx",
            ),
            models.Index(fields=["mode"], name="event_ai_qa_mode_65f568_idx"),
        ]

    def __str__(self):
        return f"AI Q&A:{self.event_id}:{self.is_enabled}"
