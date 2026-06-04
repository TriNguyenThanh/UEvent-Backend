from django.db import models

from common.models import BaseModel


class EventQuestionReply(BaseModel):
    question = models.ForeignKey(
        "interactions.EventQuestion",
        on_delete=models.CASCADE,
        related_name="replies",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_replies",
    )
    content = models.TextField()
    is_organizer_reply = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = "event_question_replies"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["question", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"Reply:{self.question_id}:{self.pk}"
