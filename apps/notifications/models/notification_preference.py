from datetime import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import models
from django.utils import timezone

from common.models import BaseModel


class NotificationPreference(BaseModel):
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    push_enabled = models.BooleanField(default=True)
    event_reminders_enabled = models.BooleanField(default=True)
    ticket_updates_enabled = models.BooleanField(default=True)
    organizer_updates_enabled = models.BooleanField(default=True)
    marketing_enabled = models.BooleanField(default=False)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(blank=True, null=True)
    quiet_hours_end = models.TimeField(blank=True, null=True)
    timezone = models.CharField(max_length=64, default="Asia/Bangkok")

    class Meta(BaseModel.Meta):
        db_table = "notification_preferences"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["push_enabled"]),
        ]

    def __str__(self):
        return f"Notification preference for {self.user_id}"

    def allows_push(self, *, category: str, now=None) -> bool:
        if not self.push_enabled:
            return False

        category_allowed = {
            "event": self.event_reminders_enabled,
            "ticket": self.ticket_updates_enabled,
            "organizer": self.organizer_updates_enabled,
            "marketing": self.marketing_enabled,
            "system": True,
        }.get(category, True)
        if not category_allowed:
            return False

        if not self.quiet_hours_enabled:
            return True

        if self.quiet_hours_start is None or self.quiet_hours_end is None:
            return True

        local_time = self._local_time(now=now)
        return not self._is_in_quiet_hours(local_time)

    def _local_time(self, *, now=None) -> time:
        current = now or timezone.now()
        try:
            tz = ZoneInfo(self.timezone or "UTC")
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")
        return timezone.localtime(current, tz).time()

    def _is_in_quiet_hours(self, current: time) -> bool:
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        if start == end:
            return True
        if start < end:
            return start <= current < end
        return current >= start or current < end
