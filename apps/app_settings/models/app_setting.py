from django.db import models
from common.models import BaseModel

class AppSetting(BaseModel):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True, null=True)
    updated_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_settings"
    )

    class Meta(BaseModel.Meta):
        db_table = "app_settings"
        ordering = ["key"]
        indexes = [
            models.Index(fields=["key"]),
        ]

    def __str__(self):
        return self.key
