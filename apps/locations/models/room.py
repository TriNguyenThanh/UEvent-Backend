from django.db import models
from common.models import BaseModel


class Room(BaseModel):
    building = models.ForeignKey("locations.Building", on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        db_table = "rooms"
        ordering = ["building__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["building", "code"], name="uq_rooms_building_code")
        ]
        indexes = [models.Index(fields=["building", "name"]), models.Index(fields=["building", "code"])]

    def __str__(self):
        return f"{self.building.code} - {self.name}"

