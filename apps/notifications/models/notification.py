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
        REGISTRATION_CONFIRMED = "registration_confirmed", "Registration Confirmed"
        REGISTRATION_WAITLISTED = "registration_waitlisted", "Registration Waitlisted"
        NEW_REGISTRATION = "new_registration", "New Registration"
        ORGANIZER_ANNOUNCEMENT = "organizer_announcement", "Organizer Announcement"
        QUESTION_ANSWERED = "question_answered", "Question Answered"
        ORGANIZER_REQUEST_APPROVED = "organizer_request_approved", "Organizer Request Approved"
        ORGANIZER_REQUEST_REJECTED = "organizer_request_rejected", "Organizer Request Rejected"
        EVENT_UPDATE = "event_update", "Event Update"

    class NotificationCategory(models.TextChoices):
        TICKET = "ticket", "Ticket"
        ORGANIZER = "organizer", "Organizer"
        EVENT = "event", "Event"
        MARKETING = "marketing", "Marketing"
        SYSTEM = "system", "System"

    class NotificationTarget(models.TextChoices):
        EVENT_USER = "event_user", "Event User"
        EVENT_ORGANIZER = "event_organizer", "Event Organizer"
        TICKET = "ticket", "Ticket"
        ORGANIZER_REGISTRATIONS = "organizer_registrations", "Organizer Registrations"
        ORGANIZER_QUESTIONS = "organizer_questions", "Organizer Questions"
        QUESTION_DETAIL = "question_detail", "Question Detail"
        PROFILE = "profile", "Profile"
        NOTIFICATION_DETAIL = "notification_detail", "Notification Detail"

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
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notifications",
    )
    type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.ANNOUNCEMENT,
    )
    category = models.CharField(
        max_length=30,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM,
    )
    target = models.CharField(
        max_length=50,
        choices=NotificationTarget.choices,
        default=NotificationTarget.NOTIFICATION_DETAIL,
    )
    audience_type = models.CharField(
        max_length=20, choices=AudienceType.choices, default=AudienceType.CUSTOM
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_label = models.CharField(max_length=80, blank=True)
    action_route = models.CharField(max_length=512, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.DRAFT,
    )
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
