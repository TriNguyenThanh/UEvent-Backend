from django.db import models
from common.models import BaseModel


class Notification(BaseModel):
    class NotificationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    class NotificationType(models.TextChoices):
        ANNOUNCEMENT = "announcement", "Announcement"
        ALERT = "alert", "Alert"
        REMINDER = "reminder", "Reminder"
        PROMOTION = "promotion", "Promotion"
        INVITE = "invite", "Invite"
        TICKET_CONFIRM = "ticket_confirm", "Ticket Confirm"

    class AudienceType(models.TextChoices):
        ALL = "all", "All"
        STUDENTS = "students", "Students"
        ORGANIZERS = "organizers", "Organizers"
        ADMINS = "admins", "Admins"
        CUSTOM = "custom", "Custom"

    template = models.ForeignKey(
        "notifications.NotificationTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    event = models.ForeignKey(
        "events.Event", on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications"
    )
    created_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_notifications"
    )
    type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.ANNOUNCEMENT)
    audience_type = models.CharField(max_length=20, choices=AudienceType.choices, default=AudienceType.CUSTOM)
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.DRAFT)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
            models.Index(fields=["event", "created_at"]),
        ]

    def __str__(self):
        return self.title


