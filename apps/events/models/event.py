from django.db import models
from common.models import BaseModel


class Event(BaseModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        ACTIVE = "active", "Active"
        FINISHED = "finished", "Finished"
        CANCELLED = "cancelled", "Cancelled"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    category = models.ForeignKey("events.EventCategory", on_delete=models.RESTRICT, related_name="events")
    room = models.ForeignKey(
        "locations.Room", on_delete=models.SET_NULL, related_name="events", blank=True, null=True
    )
    created_by = models.ForeignKey(
        "users.User", on_delete=models.RESTRICT, related_name="created_events"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    registration_open_at = models.DateTimeField(blank=True, null=True)
    registration_close_at = models.DateTimeField(blank=True, null=True)
    cancellation_deadline_at = models.DateTimeField(blank=True, null=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    max_capacity = models.PositiveIntegerField(null=True, blank=True)
    location_snapshot = models.CharField(max_length=500, blank=True, null=True)
    cover_image_key = models.CharField(max_length=500, blank=True, null=True)
    deep_link = models.CharField(max_length=500, blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "events"
        ordering = ["-start_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "start_at"]),
            models.Index(fields=["category", "start_at"]),
            models.Index(fields=["created_by", "status"]),
            models.Index(fields=["room", "start_at"]),
            models.Index(fields=["start_at", "end_at"]),
        ]

    def __str__(self):
        return self.title

