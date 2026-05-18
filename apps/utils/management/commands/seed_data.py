from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


DEFAULT_SEED_FIXTURE = Path("Docs") / "database" / "data_seed.json"


class Command(BaseCommand):
    help = "Seed local development data from a JSON fixture (default: Docs/database/data_seed.json)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default=str(DEFAULT_SEED_FIXTURE),
            help="Path to JSON fixture (absolute or relative to BASE_DIR).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Flush the database before loading fixture (destructive).",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture"])
        if not fixture_path.is_absolute():
            fixture_path = settings.BASE_DIR / fixture_path
        fixture_path = fixture_path.resolve()

        if not fixture_path.exists():
            raise CommandError(f"Seed fixture not found: {fixture_path}")

        if options["reset"]:
            self.stdout.write("Flushing database ...")
            call_command("flush", interactive=False, verbosity=0)

        self.stdout.write(f"Loading seed fixture: {fixture_path}")
        call_command("loaddata", str(fixture_path), verbosity=0)

        self.stdout.write(
            self.style.SUCCESS(f"Seed data ready from fixture: {fixture_path}")
        )
