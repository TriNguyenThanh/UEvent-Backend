from django.db import models
from common.models import BaseModel


class NotificationTemplate(BaseModel):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    title_template = models.CharField(max_length=255)
    message_template = models.TextField()
    channel = models.CharField(max_length=30, default="in_app")
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        db_table = "notification_templates"
        ordering = ["name"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["channel"])]

    def __str__(self):
        return self.name


