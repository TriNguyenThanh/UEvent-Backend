from django.db import models
from common.models import BaseModel


class RegistrationFormField(BaseModel):
    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        NUMBER = "number", "Number"
        SELECT = "select", "Select"
        CHECKBOX = "checkbox", "Checkbox"
        DATE = "date", "Date"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="registration_fields")
    field_key = models.SlugField(max_length=100)
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    is_required = models.BooleanField(default=False)
    is_editable_after_submit = models.BooleanField(default=False)
    options_json = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        db_table = "registration_form_fields"
        ordering = ["event", "sort_order", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "field_key"], name="uq_registration_fields_event_key")
        ]
        indexes = [
            models.Index(fields=["event", "sort_order"]),
            models.Index(fields=["event", "field_type"]),
        ]

    def __str__(self):
        return f"{self.event} - {self.label}"


