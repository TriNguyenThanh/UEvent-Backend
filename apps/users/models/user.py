from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from common.models import BaseModel


class User(BaseModel, AbstractUser):
    student_code = models.CharField(max_length=32, blank=True, null=True, unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)

    class Meta(BaseModel.Meta):
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.get_full_name() or self.username


