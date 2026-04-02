from django.db import models
from common.models import BaseModel


class EventCategory(BaseModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        db_table = "event_categories"
        ordering = ["name"]
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["name"])]

    def __str__(self):
        return self.name


