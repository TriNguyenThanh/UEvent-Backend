from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from common.models import BaseModel


class UserAuthIdentity(BaseModel):
    class Provider(models.TextChoices):
        EMAIL = "email", "Email"
        GOOGLE = "google", "Google"
        PASSKEY = "passkey", "Passkey"

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="auth_identities")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_uid = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    last_used_at = models.DateTimeField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "user_auth_identities"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["provider", "provider_uid"], name="uq_user_auth_provider_uid")
        ]
        indexes = [
            models.Index(fields=["user", "provider"]),
            models.Index(fields=["last_used_at"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_uid}"


