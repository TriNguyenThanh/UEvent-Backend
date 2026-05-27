from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from common.models import BaseModel


class EventFeedback(BaseModel):
    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="feedbacks")
    user = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="feedbacks"
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    content = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = "event_feedbacks"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="uq_event_feedbacks_event_user")
        ]
        indexes = [
            models.Index(fields=["event", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Feedback:{self.event.pk}:{self.user.pk if self.user else 'anonymous'}"

