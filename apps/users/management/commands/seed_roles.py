from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import Role
from apps.utils.seed_data import LEGACY_SEED_ROLE_CODES, SEED_ROLE_CODES, SEED_ROLES


DEFAULT_ROLES = SEED_ROLES


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

        deleted_count, _ = Role.objects.filter(code__in=LEGACY_SEED_ROLE_CODES).exclude(
            code__in=SEED_ROLE_CODES
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded roles successfully. "
                f"created={created_count}, updated={updated_count}, deleted_legacy={deleted_count}"
            )
        )
