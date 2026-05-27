from django.db import models
from common.models import BaseModel


class SupportTicket(BaseModel):
    class TicketStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class TicketPriority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Category(models.TextChoices):
        ACCOUNT = "account", "Account"
        EVENT = "event", "Event"
        PAYMENT = "payment", "Payment"
        TECHNICAL = "technical", "Technical"
        OTHER = "other", "Other"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    priority = models.CharField(max_length=20, choices=TicketPriority.choices, default=TicketPriority.MEDIUM)
    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_support_tickets",
    )

    class Meta(BaseModel.Meta):
        db_table = "support_tickets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "priority", "updated_at"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self):
        return self.subject


