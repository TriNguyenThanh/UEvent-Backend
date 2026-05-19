import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import Role, User, UserAuthIdentity, UserRole
from apps.users.services import KeycloakProvisioningService


UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class Command(BaseCommand):
    help = "Repair local users provisioned from Keycloak before email-based username and default role enforcement."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply repairs. Without this flag the command only prints a dry-run report.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Explicitly run in dry-run mode. This is the default.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])
        if apply_changes and options["dry_run"]:
            self.stderr.write(self.style.ERROR("Use either --apply or --dry-run, not both."))
            return

        stats = {
            "scanned": 0,
            "username_updates": 0,
            "role_assignments": 0,
            "conflicts": 0,
        }

        try:
            student_role = Role.objects.get(
                code=KeycloakProvisioningService.DEFAULT_ROLE_CODE,
                is_active=True,
            )
        except Role.DoesNotExist:
            self.stderr.write(self.style.ERROR("Role 'student' is not configured. Run seed_roles first."))
            return

        queryset = (
            User.objects.filter(auth_identities__provider=UserAuthIdentity.Provider.KEYCLOAK)
            .distinct()
            .prefetch_related("user_roles__role")
            .order_by("id")
        )

        context = transaction.atomic() if apply_changes else _NoopContext()
        with context:
            for user in queryset.select_for_update() if apply_changes else queryset:
                stats["scanned"] += 1
                self._repair_user(
                    user=user,
                    student_role=student_role,
                    apply_changes=apply_changes,
                    stats=stats,
                )

        mode = "APPLIED" if apply_changes else "DRY-RUN"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: scanned={stats['scanned']}, "
                f"username_updates={stats['username_updates']}, "
                f"role_assignments={stats['role_assignments']}, "
                f"conflicts={stats['conflicts']}"
            )
        )

    def _repair_user(self, *, user, student_role, apply_changes: bool, stats: dict):
        email = KeycloakProvisioningService.normalize_email(user.email or "")
        if not email:
            stats["conflicts"] += 1
            self.stdout.write(f"SKIP {user.pk}: missing email.")
            return

        conflict = (
            User.objects.filter(username__iexact=email)
            .exclude(pk=user.pk)
            .exists()
        )
        if conflict:
            stats["conflicts"] += 1
            self.stdout.write(f"SKIP {user.pk}: username/email conflict for {email}.")
            return

        update_fields = []
        if user.username != email and (UUID_RE.match(user.username or "") or user.username.lower() != email):
            stats["username_updates"] += 1
            self.stdout.write(f"USERNAME {user.pk}: {user.username} -> {email}")
            if apply_changes:
                user.username = email
                update_fields.append("username")

        if user.email != email:
            if apply_changes:
                user.email = email
                update_fields.append("email")

        has_role = UserRole.objects.filter(user=user).exists()
        if not has_role:
            stats["role_assignments"] += 1
            self.stdout.write(f"ROLE {user.pk}: assign student")
            if apply_changes:
                UserRole.objects.create(user=user, role=student_role, is_primary=True)

        if apply_changes and update_fields:
            user.save(update_fields=[*update_fields, "updated_at"])


class _NoopContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
