from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from common.models import BaseModel


class User(BaseModel, AbstractUser):
    class AccountStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        BANNED = "banned", "Banned"

    student_code = models.CharField(max_length=32, blank=True, null=True, unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    avatar_url = models.URLField(blank=True)
    account_status = models.CharField(max_length=20, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)
    faculty = models.CharField(max_length=200, blank=True, null=True)
    class_name = models.CharField(max_length=100, blank=True, null=True)

    class Meta(BaseModel.Meta):
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["account_status"]),
        ]

    def __str__(self):
        return self.get_full_name() or self.username


