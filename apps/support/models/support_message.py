from django.db import models
from common.models import BaseModel


class SupportMessage(BaseModel):
    ticket = models.ForeignKey("support.SupportTicket", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="support_messages")
    message = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = "support_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ticket", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]

    def __str__(self):
        return f"message:{self.ticket_id}:{self.sender_id}"

