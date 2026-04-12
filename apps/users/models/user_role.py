from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone
from common.models import BaseModel


class UserRole(BaseModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey("users.Role", on_delete=models.RESTRICT, related_name="user_roles")
    is_primary = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(default=timezone.now)
    assigned_by = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_user_roles")

    class Meta(BaseModel.Meta):
        db_table = "user_roles"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="uq_user_roles_user_role"),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_primary=True),
                name="uq_user_roles_single_primary",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "is_primary"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.role}"