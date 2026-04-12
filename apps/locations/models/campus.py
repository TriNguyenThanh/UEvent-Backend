from django.db import models
from common.models import BaseModel


class Campus(BaseModel):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        db_table = "campuses"
        ordering = ["name"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["code"])]

    def __str__(self):
        return self.name


