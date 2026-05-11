from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import Role


DEFAULT_ROLES = [
    {
        "code": "student",
        "name": "Student",
        "description": "Người dùng sinh viên, có thể tham gia và đăng ký sự kiện.",
    },
    {
        "code": "organizer",
        "name": "Organizer",
        "description": "Người tổ chức sự kiện, có quyền tạo và quản lý sự kiện được phân công.",
    },
    {
        "code": "admin",
        "name": "Admin",
        "description": "Quản trị viên hệ thống, có quyền truy cập khu vực quản trị.",
    },
    {
        "code": "faculty_admin",
        "name": "Faculty Admin",
        "description": "Quản trị viên cấp khoa, quản lý dữ liệu và người dùng thuộc khoa phụ trách.",
    },
    {
        "code": "system_admin",
        "name": "System Admin",
        "description": "Quản trị viên vận hành hệ thống với quyền quản trị toàn cục.",
    },
]


class Command(BaseCommand):
    help = "Seed default user roles required by admin user management."

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for role_data in DEFAULT_ROLES:
            role, created = Role.all_objects.update_or_create(
                code=role_data["code"],
                defaults={
                    "name": role_data["name"],
                    "description": role_data["description"],
                    "is_active": True,
                    "deleted_at": None,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created role: {role.code}"))
            else:
                updated_count += 1
                self.stdout.write(f"Updated role: {role.code}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded roles successfully. created={created_count}, updated={updated_count}"
            )
        )
