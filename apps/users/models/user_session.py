from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from common.models import BaseModel


class UserSession(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="sessions")
    refresh_token_hash = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "user_sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["revoked_at"]),
        ]

    def __str__(self):
        return f"session:{self.user.pk}"