from django.db import models
from common.models import BaseModel


class EventOrganizer(BaseModel):
    class OrganizerRole(models.TextChoices):
        OWNER = "owner", "Owner"
        CO_HOST = "co_host", "Co-host"
        STAFF = "staff", "Staff"
        CHECKIN = "checkin", "Check-in"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="organizers")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="event_organizer_roles")
    role = models.CharField(max_length=20, choices=OrganizerRole.choices)

    class Meta(BaseModel.Meta):
        db_table = "event_organizers"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="uq_event_organizers_event_user")
        ]
        indexes = [models.Index(fields=["event", "role"]), models.Index(fields=["user", "role"])]

    def __str__(self):
        return f"{self.event} - {self.user} ({self.role})"


