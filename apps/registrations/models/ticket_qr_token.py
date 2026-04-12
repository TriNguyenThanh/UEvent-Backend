from django.db import models
from django.utils import timezone
from common.models import BaseModel


class TicketQrToken(BaseModel):
    ticket = models.ForeignKey("registrations.Ticket", on_delete=models.CASCADE, related_name="qr_tokens")
    token_hash = models.CharField(max_length=255, unique=True)
    issued_at = models.DateTimeField(default=timezone.now)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    class Meta(BaseModel.Meta):
        db_table = "ticket_qr_tokens"
        ordering = ["-valid_from"]
        indexes = [
            models.Index(fields=["ticket", "valid_to"]),
            models.Index(fields=["valid_from", "valid_to"]),
        ]

    def __str__(self):
        return f"QR:{self.ticket_id}:{self.valid_from.isoformat()}"


