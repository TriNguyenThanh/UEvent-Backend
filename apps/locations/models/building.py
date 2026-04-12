from django.db import models
from common.models import BaseModel


class Building(BaseModel):
    campus = models.ForeignKey("locations.Campus", on_delete=models.RESTRICT, related_name="buildings")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        db_table = "buildings"
        ordering = ["campus__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["campus", "code"], name="uq_buildings_campus_code")
        ]
        indexes = [models.Index(fields=["campus", "name"]), models.Index(fields=["campus", "code"])]

    def __str__(self):
        return f"{self.campus.code} - {self.name}"


