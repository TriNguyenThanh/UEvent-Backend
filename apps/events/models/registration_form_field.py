from django.db import models
from common.models import BaseModel


class RegistrationFormField(BaseModel):
    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        TEXTAREA = "textarea", "Text area"
        NUMBER = "number", "Number"
        SELECT = "select", "Select"
        MULTI_SELECT = "multi_select", "Multi select"
        CHECKBOX = "checkbox", "Checkbox"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="registration_fields")
    key = models.SlugField(max_length=100)
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    is_required = models.BooleanField(default=False)
    options_json = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        db_table = "registration_form_fields"
        ordering = ["event", "sort_order", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "key"], name="uq_registration_fields_event_key")
        ]
        indexes = [
            models.Index(fields=["event", "sort_order"]),
            models.Index(fields=["event", "field_type"]),
        ]

    def __str__(self):
        return f"{self.event} - {self.label}"


