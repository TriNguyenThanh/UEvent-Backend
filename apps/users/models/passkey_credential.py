from django.db import models
from django.utils import timezone

from common.models import BaseModel


class PasskeyCredential(BaseModel):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="passkey_credentials",
    )
    credential_id = models.CharField(max_length=1024, unique=True)
    public_key = models.TextField()
    sign_count = models.BigIntegerField(default=0)
    transports = models.JSONField(default=list, blank=True)
    device_name = models.CharField(max_length=120, blank=True)
    device_type = models.CharField(max_length=64, blank=True)
    backed_up = models.BooleanField(default=False)
    last_used_at = models.DateTimeField(blank=True, null=True)
    revoked_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta(BaseModel.Meta):
        db_table = "passkey_credentials"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
            models.Index(fields=["last_used_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.deleted_at is None

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at", "updated_at"])

    def mark_used(
        self,
        *,
        sign_count: int,
        device_type: str = "",
        backed_up: bool | None = None,
    ) -> None:
        self.sign_count = sign_count
        if device_type:
            self.device_type = device_type
        if backed_up is not None:
            self.backed_up = backed_up
        self.last_used_at = timezone.now()
        self.save(
            update_fields=[
                "sign_count",
                "device_type",
                "backed_up",
                "last_used_at",
                "updated_at",
            ]
        )

    def __str__(self):
        return self.device_name or f"Passkey {self.credential_id[:12]}"
