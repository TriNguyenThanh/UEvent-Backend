from django.db import models
from common.models import BaseModel


class NotificationRecipient(BaseModel):
    class DeliveryStatus(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        READ = "read", "Read"

    notification = models.ForeignKey(
        "notifications.Notification", on_delete=models.CASCADE, related_name="recipients"
    )
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="notification_recipients")
    delivery_status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.QUEUED)
    delivered_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "notification_recipients"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "user"], name="uq_notification_recipients_notification_user"
            )
        ]
        indexes = [
            models.Index(fields=["user", "delivery_status"]),
            models.Index(fields=["notification", "delivered_at"]),
        ]

    def __str__(self):
        return f"{self.notification.pk} -> {self.user.pk}"

