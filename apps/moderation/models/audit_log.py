from django.db import models
from common.models import BaseModel


class AuditLog(BaseModel):
    actor = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField(max_length=80)
    resource_type = models.CharField(max_length=80)
    resource_id = models.UUIDField(blank=True, null=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resource_type", "resource_id", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action}:{self.resource_type}"

