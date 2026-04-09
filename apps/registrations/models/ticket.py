from django.db import models
from common.models import BaseModel


class Ticket(BaseModel):
    class TicketStatus(models.TextChoices):
        ISSUED = "issued", "Issued"
        USED = "used", "Used"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    registration = models.OneToOneField(
        "registrations.EventRegistration", on_delete=models.CASCADE, related_name="ticket"
    )
    ticket_code = models.CharField(max_length=50, unique=True)
    qr_payload = models.TextField()
    qr_signature = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.ISSUED)
    expires_at = models.DateTimeField()

    class Meta(BaseModel.Meta):
        db_table = "tickets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ticket_code"]),
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["registration"]),
        ]

    def __str__(self):
        return self.ticket_code

    @classmethod
    def lock_for_checkin(cls, ticket_code):
        return cls.objects.select_for_update().select_related("registration", "registration__event").get(
            ticket_code=ticket_code
        )


