from django.db import models
from django.utils import timezone

from common.models import BaseModel


class PasskeyChallenge(BaseModel):
    class Ceremony(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        AUTHENTICATION = "authentication", "Authentication"

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="passkey_challenges",
        blank=True,
        null=True,
    )
    email = models.EmailField(blank=True)
    challenge = models.CharField(max_length=512, unique=True)
    ceremony = models.CharField(max_length=32, choices=Ceremony.choices)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta(BaseModel.Meta):
        db_table = "passkey_challenges"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ceremony", "expires_at"]),
            models.Index(fields=["user", "ceremony", "used_at"]),
            models.Index(fields=["email", "ceremony", "used_at"]),
        ]

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])

    def __str__(self):
        return f"{self.ceremony}:{self.email or self.user_id}"
